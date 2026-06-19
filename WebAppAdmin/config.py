import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

TELEGRAM_BOT_TOKEN = "8518399300:AAH0zyDqW1TSY079LlBoApI0_buJmlVLSRE"
ADMIN_CHAT_ID = "330619718"

ADMIN_HOST = os.environ.get("ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(os.environ.get("ADMIN_PORT", 5000))
ADMIN_BASE_URL = f"http://{ADMIN_HOST}:{ADMIN_PORT}"

POLL_INTERVAL_SECONDS = 10

STATUSES = {
    "new": "Новый",
    "accepted": "Принят",
    "confirmed": "Подтвержден",
    "processing": "В обработке",
    "delivered": "Доставлен",
    "cancelled": "Отменен",
}

STATUS_ORDER = ["new", "accepted", "confirmed", "processing", "delivered"]
