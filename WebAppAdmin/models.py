from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    telegram_msg_id = db.Column(db.Integer, unique=True, nullable=True)
    customer_tg_id = db.Column(db.Integer, nullable=True)
    customer_name = db.Column(db.String(255), default="")
    phone = db.Column(db.String(100), default="")
    city = db.Column(db.String(255), default="")
    items = db.Column(db.Text, default="")
    total = db.Column(db.String(100), default="")
    delivery = db.Column(db.String(100), default="")
    to_pay = db.Column(db.String(100), default="")
    order_datetime = db.Column(db.String(100), default="")
    raw_text = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="new")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "telegram_msg_id": self.telegram_msg_id,
            "customer_tg_id": self.customer_tg_id,
            "customer_name": self.customer_name,
            "phone": self.phone,
            "city": self.city,
            "items": self.items,
            "total": self.total,
            "delivery": self.delivery,
            "to_pay": self.to_pay,
            "order_datetime": self.order_datetime,
            "raw_text": self.raw_text,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
