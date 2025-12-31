"""
Демонстрация совместной работы: Я (Cursor AI) + Агенты OpenCode

Этот файл показывает, как мы работаем вместе:
1. Агент планирует
2. Я (Cursor) пишу код
3. Агент документирует
4. Агент пишет тесты
5. Я интегрирую
"""

# ========================================
# ШАГ 1: ПЛАН (создан агентом PlanningAgent)
# ========================================
"""
План создания функции напоминаний:
1. Создать функцию для поиска предстоящих бронирований
2. Добавить логику отправки напоминаний
3. Интегрировать в планировщик уведомлений
4. Добавить тесты
5. Создать документацию
"""

# ========================================
# ШАГ 2: КОД (написан мной в Cursor чате)
# ========================================
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any


async def send_booking_reminders(bot, db) -> List[int]:
    """
    Отправка напоминаний пользователям о предстоящих бронированиях
    
    Проверяет все активные бронирования, которые начинаются через час,
    и отправляет напоминания пользователям.
    
    Args:
        bot: Экземпляр Telegram бота
        db: Экземпляр базы данных
    
    Returns:
        Список ID пользователей, которым отправлены напоминания
    """
    now = datetime.now()
    reminder_time = now + timedelta(hours=1)
    
    # Находим бронирования, которые начинаются через час
    bookings = await db.fetchall("""
        SELECT b.*, u.id as user_id 
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.status = 'active'
        AND DATE(b.date) = DATE('now')
        AND (b.start_time * 60 + b.start_minute) = ?
    """, (reminder_time.hour * 60 + reminder_time.minute,))
    
    sent_to = []
    
    for booking in bookings:
        try:
            message = f"⏰ <b>Напоминание!</b>\n\n"
            message += f"Ваше бронирование начинается через час:\n\n"
            message += f"📅 {booking['date']}\n"
            message += f"⏰ {booking['start_time']}:{booking['start_minute']:02d}\n"
            message += f"🏄 {booking['board_name']}\n"
            message += f"⏱ Длительность: {booking['duration']} час(ов)\n"
            
            await bot.send_message(chat_id=booking['user_id'], text=message)
            sent_to.append(booking['user_id'])
        except Exception as e:
            print(f"Ошибка отправки напоминания пользователю {booking['user_id']}: {e}")
    
    return sent_to


# ========================================
# ШАГ 3: ДОКУМЕНТАЦИЯ (создана агентом DocumentationAgent)
# ========================================
"""
# Функция send_booking_reminders

## Назначение
Отправляет напоминания пользователям о предстоящих бронированиях за 1 час до начала.

## Параметры
- `bot`: Экземпляр Telegram бота (aiogram Bot)
- `db`: Экземпляр базы данных (Database)

## Возвращает
- `List[int]`: Список ID пользователей, которым успешно отправлены напоминания

## Пример использования
```python
from notifications.reminder_service import send_booking_reminders
from core.database import Database

db = Database()
await db.connect()
sent = await send_booking_reminders(bot, db)
print(f"Напоминания отправлены {len(sent)} пользователям")
```

## Примечания
- Функция автоматически находит бронирования, которые начинаются через час
- Работает только с активными бронированиями на сегодня
- Ошибки отправки логируются, но не прерывают выполнение
"""


# ========================================
# ШАГ 4: ТЕСТЫ (созданы агентом TestingAgent)
# ========================================
"""
# Тесты для send_booking_reminders

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from notifications.reminder_service import send_booking_reminders


@pytest.mark.asyncio
async def test_send_reminders_with_active_bookings():
    # Моки
    bot = AsyncMock()
    db = AsyncMock()
    
    # Тестовые данные
    now = datetime.now()
    reminder_time = now + timedelta(hours=1)
    
    bookings_data = [{
        'id': 1,
        'user_id': 123,
        'date': now.date(),
        'start_time': reminder_time.hour,
        'start_minute': reminder_time.minute,
        'board_name': 'Test Board',
        'duration': 2,
        'status': 'active'
    }]
    
    db.fetchall = AsyncMock(return_value=bookings_data)
    bot.send_message = AsyncMock()
    
    # Выполнение
    result = await send_booking_reminders(bot, db)
    
    # Проверки
    assert len(result) == 1
    assert result[0] == 123
    bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_reminders_no_bookings():
    bot = AsyncMock()
    db = AsyncMock()
    db.fetchall = AsyncMock(return_value=[])
    
    result = await send_booking_reminders(bot, db)
    
    assert result == []
    bot.send_message.assert_not_called()
"""


# ========================================
# ШАГ 5: ИНТЕГРАЦИЯ (добавлена мной в Cursor)
# ========================================
# В notifications/notification_scheduler.py добавляем:

"""
async def _check_and_send_reminders(self):
    \"\"\"Проверка и отправка напоминаний о бронированиях\"\"\"
    try:
        from notifications.reminder_service import send_booking_reminders
        sent = await send_booking_reminders(self.bot, self.db)
        if sent:
            self.logger.info(f"Sent reminders to {len(sent)} users")
    except Exception as e:
        self.logger.error(f"Error sending reminders: {e}")

# В методе start() добавляем вызов:
async def start(self):
    while self._running:
        await self._check_and_complete_bookings()
        await self._check_and_cancel_expired_bookings()
        await self._check_and_send_reminders()  # <-- Добавлено
        await asyncio.sleep(60)
"""


# ========================================
# ИТОГ: Совместная работа
# ========================================
"""
✅ ПЛАН -> Агент PlanningAgent создал структуру
✅ КОД -> Я (Cursor AI) написал функцию
✅ ДОКУМЕНТАЦИЯ -> Агент DocumentationAgent создал описание
✅ ТЕСТЫ -> Агент TestingAgent создал тесты
✅ ИНТЕГРАЦИЯ -> Я (Cursor AI) добавил в планировщик

РЕЗУЛЬТАТ: Быстро, качественно, с документацией и тестами!
"""

