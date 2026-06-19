import re
import requests
import logging
from datetime import datetime, timezone, timedelta

from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
_LAST_UPDATE_ID = 0


def _parse_order_fields(text: str) -> dict:
    fields = {
        "customer_name": "",
        "phone": "",
        "city": "",
        "items": "",
        "total": "",
        "delivery": "",
        "to_pay": "",
        "order_datetime": "",
    }

    patterns = {
        "customer_name": r"(?i)(?:имя|name)\s*[:|]\s*(.+)",
        "phone": r"(?i)(?:телефон|phone|tel|тел)\s*[:|]\s*(.+)",
        "city": r"(?i)(?:город|city|гор)\s*[:|]\s*(.+)",
        "items": r"(?i)(?:состав\s*заказа|items|order|товар|состав)\s*[:|]\s*(.+)",
        "total": r"(?i)(?:сумма|total|сум)\s*[:|]\s*(.+)",
        "delivery": r"(?i)(?:доставка|delivery|дост|пересылка)\s*[:|]\s*(.+)",
        "to_pay": r"(?i)(?:к\s*оплате|to\s*pay|оплата|итого)\s*[:|]\s*(.+)",
        "order_datetime": r"(?i)(?:время|дата|time|date|datetime|когда)\s*[:|]\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            fields[key] = match.group(1).strip()

    return fields


def fetch_updates(offset: int = None) -> list:
    params = {"timeout": 5, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(f"{TG_API}/getUpdates", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception as e:
        logger.error(f"Telegram API error: {e}")
    return []


def poll_orders(app):
    global _LAST_UPDATE_ID

    with app.app_context():
        from models import db, Order

        updates = fetch_updates(offset=_LAST_UPDATE_ID + 1 if _LAST_UPDATE_ID else None)

        for upd in updates:
            update_id = upd.get("update_id", 0)
            if update_id > _LAST_UPDATE_ID:
                _LAST_UPDATE_ID = update_id

            msg = upd.get("message")
            if not msg:
                continue

            msg_id = msg.get("message_id")
            tg_id = msg.get("from", {}).get("id")
            text = msg.get("text") or msg.get("caption") or ""

            if not text or text.startswith("/"):
                continue

            existing = Order.query.filter_by(telegram_msg_id=msg_id).first()
            if existing:
                continue

            recent = Order.query.filter(
                Order.raw_text == text,
                Order.created_at >= datetime.now(timezone.utc) - timedelta(hours=1),
            ).first()
            if recent:
                logger.debug(f"Skipping duplicate (raw_text matches order #{recent.id})")
                continue

            parsed = _parse_order_fields(text)

            order = Order(
                telegram_msg_id=msg_id,
                customer_tg_id=tg_id,
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
            logger.info(f"Saved order #{msg_id} from tg user {tg_id}")

        logger.debug(f"Polled {len(updates)} updates")
