"""Конфигурация приложения"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс конфигурации"""
    
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Database
    DB_NAME = os.getenv("DB_NAME", "supbot.db")
    
    # Working hours
    WORK_HOURS_START = int(os.getenv("WORK_HOURS_START", 8))
    WORK_HOURS_END = int(os.getenv("WORK_HOURS_END", 22))
    
    # Payment timeout (minutes)
    PAYMENT_TIMEOUT_MINUTES = int(os.getenv("PAYMENT_TIMEOUT_MINUTES", 30))
    
    # Weather
    OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "")
    
    # Payments
    PAYMENTS_PROVIDER_TOKEN = os.getenv("PAYMENTS_PROVIDER_TOKEN", "")
    PAYMENT_CARD_DETAILS = os.getenv("PAYMENT_CARD_DETAILS", "")
    
    # Commission
    PLATFORM_COMMISSION_PERCENT = float(os.getenv("PLATFORM_COMMISSION_PERCENT", 10.0))
    
    # Review channel
    REVIEW_CHANNEL_ID = os.getenv("REVIEW_CHANNEL_ID", "")
    
    # YooKassa
    YK_SHOP_ID = os.getenv("YK_SHOP_ID", "")
    YK_SECRET = os.getenv("YK_SECRET", "")
    YK_API_URL = "https://api.yookassa.ru/v3"
    
    # Admins
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = []
    if admin_ids_str and admin_ids_str.strip() and not admin_ids_str.startswith("your_"):
        try:
            ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip() and id.strip().isdigit()]
        except (ValueError, AttributeError):
            ADMIN_IDS = []
    
    # Mini App
    MINIAPP_URL = os.getenv("MINIAPP_URL", "")
    
    # Flask
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
    
    # Yandex Maps
    YANDEX_MAPS_API_KEY = os.getenv("YANDEX_MAPS_API_KEY", "")
    
    # AI / OpenCode
    AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
    OPENCODE_PATH = os.getenv("OPENCODE_PATH", "")  # Путь к opencode (если не в PATH)
    
    @classmethod
    def validate(cls):
        """Проверка обязательных параметров"""
        required = ["BOT_TOKEN"]
        missing = []
        
        # Проверяем BOT_TOKEN (должен быть установлен и не быть заглушкой)
        bot_token = getattr(cls, "BOT_TOKEN", "")
        if not bot_token or bot_token.startswith("your_") or "here" in bot_token.lower():
            missing.append("BOT_TOKEN")
        
        if missing:
            raise ValueError(
                f"Missing or invalid required environment variables: {', '.join(missing)}\n"
                f"Please edit the .env file and set correct values."
            )

