"""Утилиты для парсинга дат"""
from datetime import date, datetime
import re
import logging

logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date | None:
    """Парсинг даты из строки в формате ДД.ММ.ГГГГ или ДД/ММ/ГГГГ"""
    if not date_str:
        return None
    
    # Убираем пробелы
    date_str = date_str.strip()
    
    # Пробуем разные форматы
    formats = [
        "%d.%m.%Y",  # 25.12.2024
        "%d/%m/%Y",  # 25/12/2024
        "%d-%m-%Y",  # 25-12-2024
        "%d.%m.%y",  # 25.12.24
        "%d/%m/%y",  # 25/12/24
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.date()
        except ValueError:
            continue
    
    return None


def is_date_valid(booking_date: date, min_days_ahead: int = 0) -> tuple[bool, str]:
    """Проверка валидности даты бронирования"""
    from datetime import timedelta
    today = date.today()
    
    if booking_date < today:
        return False, "❌ Нельзя бронировать на прошедшую дату"
    
    if booking_date == today and min_days_ahead > 0:
        return False, f"❌ Бронирование на сегодня недоступно. Минимум {min_days_ahead} дней вперед"
    
    # Максимум 30 дней вперед
    max_date = today + timedelta(days=30)
    if booking_date > max_date:
        return False, "❌ Можно бронировать максимум на 30 дней вперед"
    
    return True, ""


async def parse_date_natural_language(text: str) -> date | None:
    """Парсинг даты из естественного языка с помощью AI (опционально)"""
    from config import Config
    
    # Сначала пробуем стандартный парсер
    result = parse_date(text)
    if result:
        return result
    
    # Если стандартный парсер не сработал и AI включен, пробуем через AI
    if Config.AI_ENABLED:
        try:
            from services.ai_service import get_ai_service
            ai_service = get_ai_service()
            if ai_service.enabled:
                ai_date_str = await ai_service.parse_date_from_text(text)
                if ai_date_str:
                    result = parse_date(ai_date_str)
                    if result:
                        logger.info(f"Successfully parsed date '{text}' via AI: {result}")
                        return result
        except Exception as e:
            logger.debug(f"AI date parsing failed: {e}")
    
    return None

