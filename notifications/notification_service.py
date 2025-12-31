"""Сервис для отправки уведомлений"""
import logging
from typing import Optional
from aiogram import Bot
from core.database import Database

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
    
    async def notify_partner_new_booking(self, partner_id: int, booking_id: int):
        """Уведомление партнеру о новом бронировании"""
        try:
            partner = await self.db.fetchone(
                "SELECT telegram_id FROM partners WHERE id = ?",
                (partner_id,)
            )
            
            if not partner:
                logger.warning(f"Partner {partner_id} not found")
                return
            
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                logger.warning(f"Booking {booking_id} not found")
                return
            
            text = f"📋 <b>Новое бронирование #{booking_id}</b>\n\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Дата: {booking['date']}\n"
            text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
            text += f"Длительность: {booking['duration']} минут\n"
            text += f"Количество: {booking['quantity']}\n"
            text += f"Сумма: {booking['amount']:.2f}₽\n\n"
            text += "Используйте /partner для управления бронированием."
            
            await self.bot.send_message(
                chat_id=partner['telegram_id'],
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending notification to partner: {e}")
    
    async def notify_user_booking_confirmed(self, user_id: int, booking_id: int):
        """Уведомление пользователю о подтверждении бронирования"""
        try:
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            text = f"✅ <b>Бронирование #{booking_id} подтверждено!</b>\n\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Дата: {booking['date']}\n"
            text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n\n"
            text += "Ждем вас!"
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending notification to user: {e}")
    
    async def notify_user_booking_canceled(self, user_id: int, booking_id: int, reason: str = ""):
        """Уведомление пользователю об отмене бронирования"""
        try:
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            text = f"❌ <b>Бронирование #{booking_id} отменено</b>\n\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Дата: {booking['date']}\n"
            text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
            if reason:
                text += f"\nПричина: {reason}\n"
            text += "\nЕсли вы уже произвели оплату, средства будут возвращены."
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending cancellation notification: {e}")
    
    async def notify_admins_new_booking(self, booking_id: int):
        """Уведомление админам о новом бронировании"""
        try:
            from config import Config
            
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            text = f"📋 <b>Новое бронирование #{booking_id}</b>\n\n"
            text += f"Пользователь: {booking['user_id']}\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Сумма: {booking['amount']:.2f}₽\n"
            text += f"Статус: {booking['status']}"
            
            # Отправляем всем админам
            for admin_id in Config.ADMIN_IDS:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=text
                    )
                except Exception as e:
                    logger.error(f"Error sending notification to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error notifying admins: {e}")
    
    async def notify_partner_approved(self, partner_id: int):
        """Уведомление партнеру об одобрении заявки"""
        try:
            partner = await self.db.fetchone(
                "SELECT telegram_id, name FROM partners WHERE id = ?",
                (partner_id,)
            )
            
            if not partner:
                return
            
            text = f"✅ <b>Ваша заявка на партнерство одобрена!</b>\n\n"
            text += f"Добро пожаловать в SUPFLOT, {partner['name']}!\n\n"
            text += f"Используйте команду /partner для доступа к партнерской панели."
            
            await self.bot.send_message(
                chat_id=partner['telegram_id'],
                text=text
            )
        except Exception as e:
            logger.error(f"Error sending approval notification: {e}")
    
    async def notify_user_booking_completed(self, user_id: int, booking_id: int):
        """Уведомление пользователю о завершении бронирования с предложением оставить отзыв"""
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            text = f"✅ <b>Бронирование #{booking_id} завершено!</b>\n\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Дата: {booking['date']}\n"
            text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n\n"
            text += "Спасибо, что выбрали SUPFLOT! 🏄\n\n"
            text += "Поделитесь вашим опытом и оставьте отзыв - это поможет другим пользователям!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=f"review:booking:{booking_id}")],
                [InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings")]
            ])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending completion notification: {e}")
