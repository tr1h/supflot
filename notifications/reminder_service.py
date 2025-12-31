"""Сервис для отправки напоминаний о бронированиях"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from aiogram import Bot
from core.database import Database

logger = logging.getLogger(__name__)


async def send_booking_reminders(bot: Bot, db: Database) -> List[int]:
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
    try:
        now = datetime.now()
        reminder_time = now + timedelta(hours=1)
        
        # Находим бронирования, которые начинаются через час
        # Проверяем на сегодня и время совпадает с reminder_time
        target_minutes = reminder_time.hour * 60 + reminder_time.minute
        
        bookings = await db.fetchall("""
            SELECT b.*, u.id as user_id 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.status = 'active'
            AND DATE(b.date) = DATE('now')
            AND (b.start_time * 60 + COALESCE(b.start_minute, 0)) = ?
        """, (target_minutes,))
        
        if not bookings:
            logger.debug("No bookings to remind about")
            return []
        
        sent_to = []
        
        for booking in bookings:
            try:
                # Формируем сообщение
                message = f"⏰ <b>Напоминание!</b>\n\n"
                message += f"Ваше бронирование начинается через час:\n\n"
                message += f"📅 Дата: {booking['date']}\n"
                message += f"⏰ Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
                message += f"🏄 Доска: {booking['board_name']}\n"
                message += f"⏱ Длительность: {booking['duration']} час(ов)\n"
                if booking.get('quantity', 1) > 1:
                    message += f"📊 Количество: {booking['quantity']}\n"
                
                # Отправляем напоминание
                await bot.send_message(
                    chat_id=booking['user_id'],
                    text=message,
                    parse_mode="HTML"
                )
                sent_to.append(booking['user_id'])
                logger.info(f"Reminder sent to user {booking['user_id']} for booking {booking['id']}")
                
            except Exception as e:
                logger.error(f"Error sending reminder to user {booking['user_id']}: {e}")
        
        if sent_to:
            logger.info(f"Sent {len(sent_to)} booking reminders")
        
        return sent_to
        
    except Exception as e:
        logger.error(f"Error in send_booking_reminders: {e}", exc_info=True)
        return []


async def send_booking_reminder_for_user(bot: Bot, db: Database, user_id: int, booking_id: int) -> bool:
    """
    Отправка напоминания конкретному пользователю о конкретном бронировании
    
    Args:
        bot: Экземпляр Telegram бота
        db: Экземпляр базы данных
        user_id: ID пользователя
        booking_id: ID бронирования
    
    Returns:
        True если напоминание отправлено успешно, False иначе
    """
    try:
        booking = await db.fetchone("""
            SELECT * FROM bookings 
            WHERE id = ? AND user_id = ? AND status = 'active'
        """, (booking_id, user_id))
        
        if not booking:
            logger.warning(f"Booking {booking_id} not found or not active for user {user_id}")
            return False
        
        message = f"⏰ <b>Напоминание о бронировании</b>\n\n"
        message += f"📅 Дата: {booking['date']}\n"
        message += f"⏰ Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
        message += f"🏄 Доска: {booking['board_name']}\n"
        message += f"⏱ Длительность: {booking['duration']} час(ов)\n"
        
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"Reminder sent to user {user_id} for booking {booking_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending reminder to user {user_id} for booking {booking_id}: {e}")
        return False

