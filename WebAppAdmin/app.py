import logging
import json
import requests
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash, Response
from apscheduler.schedulers.background import BackgroundScheduler

from config import DATABASE_PATH, STATUSES, STATUS_ORDER, POLL_INTERVAL_SECONDS, TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID
from models import db, Order
from bot_listener import _parse_order_fields

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "admin-secret-key-change-me"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route("/")
def index():
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "").strip()

    query = Order.query

    if status_filter in STATUSES:
        query = query.filter_by(status=status_filter)

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Order.customer_name.ilike(like),
                Order.phone.ilike(like),
                Order.city.ilike(like),
                Order.items.ilike(like),
            )
        )

    orders = query.order_by(Order.created_at.desc()).all()
    return render_template(
        "index.html",
        orders=orders,
        statuses=STATUSES,
        status_order=STATUS_ORDER,
        current_status=status_filter,
        search=search,
    )


@app.route("/update_status/<int:order_id>", methods=["POST"])
def update_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Заказ не найден", "danger")
        return redirect(url_for("index"))

    new_status = request.form.get("status", "")
    if new_status in STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Статус заказа #{order.id} изменён на «{STATUSES[new_status]}»", "success")
    else:
        flash("Некорректный статус", "danger")

    return redirect(request.referrer or url_for("index"))


@app.route("/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Заказ не найден", "danger")
        return redirect(url_for("index"))

    order.status = "cancelled"
    db.session.commit()
    flash(f"Заказ #{order.id} отменён", "warning")
    return redirect(request.referrer or url_for("index"))


@app.route("/ingest", methods=["POST"])
def ingest_order():
    data = request.get_json(silent=True) or {}
    if not data:
        return Response(
            json.dumps({"ok": False, "error": "empty request"}),
            status=400,
            content_type="application/json",
        )

    name = data.get("name", "")
    phone = data.get("phone", "")
    items = data.get("items", [])
    subtotal = data.get("subtotal", 0)
    delivery = data.get("delivery", 0)
    total = data.get("total", 0)
    currency = data.get("currency", "L")

    if not name or not phone or not items:
        return Response(
            json.dumps({"ok": False, "error": "Missing required fields: name, phone, items"}),
            status=400,
            content_type="application/json",
        )

    items_str = ", ".join(
        f'{i.get("name", "")} x{i.get("qty", 1)} = {int(i.get("price", 0)) * int(i.get("qty", 1))} {currency}'
        for i in items
    )

    raw_lines = [
        "\U0001f36a <b>Новый заказ!</b>",
        "",
        f"\U0001f464 <b>Имя:</b> {name}",
        f"\U0001f4de <b>Телефон:</b> {phone}",
        "\U0001f4cd <b>Город:</b> Chi\u0219in\u0103u",
        "",
        "\U0001f4e6 <b>Состав заказа:</b>",
    ]
    for i in items:
        line_total = int(i.get("price", 0)) * int(i.get("qty", 1))
        raw_lines.append(f"  \u2022 {i.get('name', '')} \u00d7 {i.get('qty', 1)} = {line_total} {currency}")
    raw_lines.extend([
        "",
        f"\U0001f4b0 <b>Сумма:</b> {subtotal} {currency}",
        f"\U0001f69a <b>Доставка:</b> {delivery} {currency}",
        f"\U0001f4b5 <b>К оплате:</b> <b>{total} {currency}</b>",
        "",
        f"\U0001f550 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    ])
    raw_text = "\n".join(raw_lines)

    try:
        order = Order(
            customer_name=name,
            phone=phone,
            city="Chi\u0219in\u0103u",
            items=items_str,
            total=f"{subtotal} {currency}",
            delivery=f"{delivery} {currency}",
            to_pay=f"{total} {currency}",
            order_datetime=datetime.now().strftime("%d.%m.%Y %H:%M"),
            raw_text=raw_text,
            status="new",
        )
        db.session.add(order)
        db.session.commit()
        logger.info(f"Order #{order.id} ingested via webhook")

        return Response(
            json.dumps({"ok": True, "order_id": order.id}),
            status=200,
            content_type="application/json",
        )
    except Exception as e:
        logger.error(f"Failed to ingest order: {e}")
        return Response(
            json.dumps({"ok": False, "error": str(e)}),
            status=500,
            content_type="application/json",
        )


@app.route("/proxy/sendMessage", methods=["POST"])
def proxy_send_message():
    data = request.get_json(silent=True) or request.form.to_dict()
    if not data:
        return Response(
            json.dumps({"ok": False, "error": "empty request"}),
            status=400,
            content_type="application/json",
        )

    text = data.get("text", "")
    chat_id = data.get("chat_id")

    if text:
        parsed = _parse_order_fields(text)
        try:
            order = Order(
                customer_name=parsed["customer_name"],
                phone=parsed["phone"],
                city=parsed["city"],
                items=parsed["items"],
                total=parsed["total"],
                delivery=parsed["delivery"],
                to_pay=parsed["to_pay"],
                order_datetime=parsed["order_datetime"],
                raw_text=text,
                status="new",
            )
            db.session.add(order)
            db.session.commit()
            logger.info(f"Order #{order.id} saved via proxy")
        except Exception as e:
            logger.error(f"Failed to save order: {e}")

    tg_resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json=data,
        timeout=10,
    )
    return Response(
        tg_resp.content,
        status=tg_resp.status_code,
        content_type="application/json",
    )


def start_polling():
    from bot_listener import poll_orders

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=poll_orders,
        trigger="interval",
        seconds=POLL_INTERVAL_SECONDS,
        args=[app],
        id="telegram_poll",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Telegram polling started (every {POLL_INTERVAL_SECONDS}s)")


if __name__ == "__main__":
    start_polling()
    app.run(debug=True, use_reloader=False)
