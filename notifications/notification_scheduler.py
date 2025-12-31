"""Планировщик уведомлений и фоновых задач"""
import asyncio
import logging
from datetime import datetime
from core.database import Database
from services.booking_service import BookingService
from config import Config

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Планировщик для автоматических задач"""
    
    def __init__(self, db: Database, bot=None):
        self.db = db
        self.bot = bot
        self.booking_service = BookingService(db)
        self._running = False
    
    async def start(self):
        """Запуск планировщика"""
        self._running = True
        logger.info("Notification scheduler started")
        
        while self._running:
            try:
                await self._check_and_complete_bookings()
                await self._check_and_cancel_expired_payments()
                await self._check_and_send_reminders()
                await asyncio.sleep(60)  # Проверяем каждые 60 секунд
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Остановка планировщика"""
        self._running = False
        logger.info("Notification scheduler stopped")
    
    async def _check_and_complete_bookings(self):
        """Проверка и завершение истекших бронирований"""
        try:
            bookings = await self.booking_service.get_active_bookings_to_complete()
            
            for booking in bookings:
                user_id = booking['user_id']
                await self._complete_booking(booking['id'])
                
                # Уведомляем пользователя о завершении и предлагаем оставить отзыв
                if self.bot:
                    try:
                        from notifications.notification_service import NotificationService
                        notification_service = NotificationService(self.bot, self.db)
                        await notification_service.notify_user_booking_completed(user_id, booking['id'])
                    except Exception as e:
                        logger.error(f"Error sending completion notification: {e}")
                
        except Exception as e:
            logger.error(f"Error checking bookings: {e}")
    
    async def _complete_booking(self, booking_id: int):
        """Завершение бронирования и начисление средств партнеру"""
        try:
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            # Обновляем статус
            await self.db.execute(
                "UPDATE bookings SET status = 'completed' WHERE id = ?",
                (booking_id,)
            )
            
            # Если платеж не через Telegram, начисляем средства партнеру
            if booking['payment_method'] != 'telegram' and booking['partner_id']:
                await self._credit_partner_wallet(booking)
            
            logger.info(f"Booking {booking_id} completed automatically")
            
        except Exception as e:
            logger.error(f"Error completing booking {booking_id}: {e}")
    
    async def _credit_partner_wallet(self, booking: dict):
        """Начисление средств на кошелек партнера"""
        try:
            partner_id = booking['partner_id']
            amount = booking['amount']
            
            # Получаем комиссию платформы
            platform_commission = Config.PLATFORM_COMMISSION_PERCENT
            partner_amount = amount * (1 - platform_commission / 100)
            
            # Если есть сотрудник, вычитаем его комиссию
            if booking.get('employee_id'):
                employee = await self.db.fetchone(
                    "SELECT commission_percent FROM employees WHERE id = ?",
                    (booking['employee_id'],)
                )
                if employee:
                    employee_commission = employee['commission_percent']
                    employee_amount = partner_amount * (employee_commission / 100)
                    partner_amount -= employee_amount
                    
                    # Начисляем сотруднику
                    await self.db.execute(
                        """INSERT INTO partner_wallet_ops (partner_id, type, amount, src, booking_id)
                           VALUES (?, 'credit', ?, ?, ?)""",
                        (booking['employee_id'], employee_amount, f"Комиссия за бронирование #{booking['id']}", booking['id'])
                    )
            
            # Начисляем партнеру
            await self.db.execute(
                """INSERT INTO partner_wallet_ops (partner_id, type, amount, src, booking_id)
                   VALUES (?, 'credit', ?, ?, ?)""",
                (partner_id, partner_amount, f"Бронирование #{booking['id']}", booking['id'])
            )
            
            logger.info(f"Credited {partner_amount:.2f} to partner {partner_id} for booking {booking['id']}")
            
        except Exception as e:
            logger.error(f"Error crediting partner wallet: {e}")
    
    async def _check_and_cancel_expired_payments(self):
        """Проверка и отмена просроченных неоплаченных бронирований"""
        try:
            now = datetime.now()
            
            # Получаем бронирования, у которых истек срок оплаты и они еще не оплачены
            expired_bookings = await self.db.fetchall(
                """SELECT * FROM bookings 
                   WHERE payment_deadline IS NOT NULL 
                   AND payment_deadline < ? 
                   AND status IN ('waiting_partner', 'waiting_card', 'waiting_cash')""",
                (now,)
            )
            
            for booking in expired_bookings:
                await self._cancel_expired_booking(booking['id'])
                
        except Exception as e:
            logger.error(f"Error checking expired payments: {e}")
    
    async def _cancel_expired_booking(self, booking_id: int):
        """Отмена просроченного бронирования"""
        try:
            booking = await self.db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            if not booking:
                return
            
            # Обновляем статус на отмененный
            await self.db.execute(
                "UPDATE bookings SET status = 'canceled' WHERE id = ?",
                (booking_id,)
            )
            
            logger.info(f"Booking {booking_id} canceled due to payment timeout")
            
            # Отправляем уведомление пользователю (если есть бот)
            if self.bot:
                try:
                    user = await self.db.fetchone(
                        "SELECT id FROM users WHERE id = ?",
                        (booking['user_id'],)
                    )
                    if user:
                        text = f"⏰ <b>Бронирование #{booking_id} отменено</b>\n\n"
                        text += "К сожалению, время на оплату истекло.\n"
                        text += "Ваше бронирование было автоматически отменено.\n\n"
                        text += "Вы можете создать новое бронирование в любое время."
                        
                        await self.bot.send_message(
                            chat_id=booking['user_id'],
                            text=text
                        )
                except Exception as e:
                    logger.error(f"Error sending expiration notification to user: {e}")
            
        except Exception as e:
            logger.error(f"Error canceling expired booking {booking_id}: {e}")
    
    async def _check_and_send_reminders(self):
        """Проверка и отправка напоминаний о предстоящих бронированиях"""
        try:
            if not self.bot:
                return
            
            from notifications.reminder_service import send_booking_reminders
            sent = await send_booking_reminders(self.bot, self.db)
            
            if sent:
                logger.info(f"Sent booking reminders to {len(sent)} users")
                
        except Exception as e:
            logger.error(f"Error sending booking reminders: {e}")

