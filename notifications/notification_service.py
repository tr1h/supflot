# notifications/notification_service.py
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Добавляем импорт Database
from core.database import Database

from .notification_scheduler import NotificationScheduler

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Bot, db: Database):  # Теперь Database будет определен
        self.bot = bot
        self.db = db
        self.scheduler = NotificationScheduler(bot)

    async def send_notification(self, user_id: int, message: str, buttons=None):
        """Отправляет уведомление пользователю"""
        try:
            await self.bot.send_message(user_id, message, reply_markup=buttons)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            return False

    async def notify_admins(self, message: str, buttons=None):
        """Отправляет уведомление всем администраторам"""
        admins = await self.db.execute("SELECT user_id FROM admins", fetchall=True)
        for (admin_id,) in admins:
            await self.send_notification(admin_id, message, buttons)

    async def notify_new_booking(self, booking_id: int):
        """Уведомление о новой брони"""
        try:
            # Получаем данные о бронировании
            booking = await self.db.execute(
                """
                SELECT bk.id, u.full_name, b.name, bk.date, bk.start_time, bk.duration, 
                       bk.quantity, bk.amount, p.telegram_id, u.id as user_id
                FROM bookings bk
                JOIN boards b ON bk.board_id = b.id
                JOIN partners p ON b.partner_id = p.id
                JOIN users u ON bk.user_id = u.id
                WHERE bk.id = ?
                """,
                (booking_id,),
                fetch=True
            )

            if not booking:
                return

            (_, user_name, board_name, date, start_time, duration,
             quantity, amount, partner_id, user_id) = booking

            end_time = start_time + duration

            # Уведомление админам
            admin_msg = new_booking_admin(
                booking_id, user_name, board_name, date, start_time, end_time, quantity, amount
            )
            await self.notify_admins(admin_msg)

            # Уведомление партнеру
            if partner_id:
                partner_msg, partner_kb = new_booking_partner(
                    booking_id, user_name, board_name, date, start_time, end_time, quantity, amount
                )
                await self.send_notification(partner_id, partner_msg, partner_kb)

            # Уведомление пользователю
            user_msg = (
                "🎉 Ваша бронь оформлена!\n"
                f"🏄 {board_name}\n"
                f"📅 {date} {start_time}:00–{end_time}:00\n"
                f"🔢 {quantity} шт.\n"
                f"💰 {amount:.2f} ₽\n\n"
                "Мы напомним вам о бронировании перед началом."
            )
            await self.send_notification(user_id, user_msg)

            # Планируем напоминания
            await self.scheduler.schedule_booking_reminders(
                booking_id, date, start_time, user_id, partner_id
            )

            # Планируем уведомления о начале и окончании
            await self.schedule_booking_notifications(
                booking_id, date, start_time, end_time, user_id, partner_id
            )

        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений о новой брони: {e}")

    async def schedule_booking_notifications(self, booking_id: int, date: str, start_time: int,
                                             end_time: int, user_id: int, partner_id: int):
        """Планирует уведомления о бронировании по времени"""
        try:
            start_dt = datetime.strptime(f"{date} {start_time}:00", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}:00", "%Y-%m-%d %H:%M")

            # Уведомление за 1 час до начала
            remind_start = start_dt - timedelta(hours=1)
            if remind_start > datetime.now():
                user_msg = reminder_before_start_user(start_time, end_time)
                await self.scheduler.schedule_reminder(remind_start, user_id, user_msg)

            # Уведомление за 30 минут до окончания
            remind_end = end_dt - timedelta(minutes=30)
            if remind_end > datetime.now():
                user_msg = reminder_before_end_user(end_time)
                await self.scheduler.schedule_reminder(remind_end, user_id, user_msg)

            # Уведомление после окончания
            await self.scheduler.schedule_reminder(
                end_dt + timedelta(minutes=5),
                user_id,
                *booking_finished()
            )

        except Exception as e:
            logger.error(f"Ошибка планирования уведомлений: {e}")

    async def notify_booking_confirmation(self, booking_id: int, confirmed: bool):
        """Уведомляет пользователя о подтверждении/отклонении брони"""
        try:
            booking = await self.db.execute(
                "SELECT user_id, board_id, date, start_time, duration FROM bookings WHERE id = ?",
                (booking_id,),
                fetch=True
            )

            if not booking:
                return

            user_id, board_id, date, start_time, duration = booking
            end_time = start_time + duration

            if confirmed:
                # Получаем название доски
                board_name = await self.db.execute(
                    "SELECT name FROM boards WHERE id = ?", (board_id,), fetch="scalar"
                ) or "доска"

                message = booking_confirmed_user(board_name, date, start_time, end_time)
            else:
                message = booking_rejected_user()

            await self.send_notification(user_id, message)
        except Exception as e:
            logger.error(f"Ошибка уведомления о подтверждении брони: {e}")

    async def notify_payment(self, user_id: int, amount: float, success: bool):
        """Уведомление о платеже"""
        try:
            if success:
                message = payment_success(amount)
            else:
                message = payment_failed()

            await self.send_notification(user_id, message)
        except Exception as e:
            logger.error(f"Ошибка уведомления о платеже: {e}")

    async def notify_withdraw_request(self, partner_id: int, amount: float):
        """Уведомление о запросе выплаты"""
        try:
            message = withdraw_requested(amount)
            await self.send_notification(partner_id, message)

            # Уведомление админам
            admin_msg, admin_kb = new_withdraw_admin(partner_id, amount)
            await self.notify_admins(admin_msg, admin_kb)
        except Exception as e:
            logger.error(f"Ошибка уведомления о выплате: {e}")

    async def cancel_booking_notifications(self, booking_id: int):
        """Отменяет все запланированные уведомления для брони"""
        self.scheduler.cancel_booking_reminders(booking_id)