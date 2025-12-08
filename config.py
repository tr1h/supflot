import os
from dotenv import load_dotenv
from typing import Optional

# Загрузить переменные из .env
load_dotenv()

# --- Telegram ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN") or ""
if not BOT_TOKEN:
    raise RuntimeError("❌ Переменная BOT_TOKEN не указана в .env")

# --- База данных ---
DB_NAME: str = os.getenv("DB_NAME", "supbot.db")  # По умолчанию: supbot.db

# --- Часы работы ---
WORK_HOURS_START: int = int(os.getenv("WORK_HOURS_START", 8))
WORK_HOURS_END: int = int(os.getenv("WORK_HOURS_END", 22))
WORK_HOURS: tuple[int, int] = (WORK_HOURS_START, WORK_HOURS_END)

# --- Погода ---
OPENWEATHER_KEY: str = os.getenv("OPENWEATHER_KEY", "")

# --- Оплата ---
PAYMENTS_PROVIDER_TOKEN: str = os.getenv("PAYMENTS_PROVIDER_TOKEN", "")
PAYMENT_CARD_DETAILS: str = os.getenv(
    "PAYMENT_CARD_DETAILS",
    "Переводите на карту 5536 9138 6034 5798 Александр Г."
)

# --- Комиссия ---
PLATFORM_COMMISSION_PERCENT: float = float(os.getenv("PLATFORM_COMMISSION_PERCENT", 10))

# --- Канал отзывов ---
REVIEW_CHANNEL: str = os.getenv("REVIEW_CHANNEL_ID", "@default_channel")

# --- ЮKassa (если используется) ---
YK_SHOP_ID: Optional[str] = os.getenv("YK_SHOP_ID")
YK_SECRET: Optional[str] = os.getenv("YK_SECRET")

# --- Администраторы ---
_admins_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x) for x in _admins_raw.split(",") if x.strip().isdigit()] or [
    202140267,
    1383730017,
]
DEFAULT_EMPLOYEE_COMMISSION_PERCENT = 30.0  # %