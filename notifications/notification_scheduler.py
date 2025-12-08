import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot

logger = logging.getLogger(__name__)


class NotificationScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduled_tasks = defaultdict(dict)

    async def schedule_reminder(self, when: datetime, user_id: int, message: str, buttons=None):
        """Планирует напоминание на определенное время"""
        try:
            now = datetime.now()
            if when <= now:
                return

            delay = (when - now).total_seconds()
            task = asyncio.create_task(self._send_reminder(delay, user_id, message, buttons))
            self.scheduled_tasks[user_id][when] = task
        except Exception as e:
            logger.error(f"Ошибка планирования напоминания: {e}")

    async def _send_reminder(self, delay: float, user_id: int, message: str, buttons=None):
        """Отправляет напоминание после задержки"""
        try:
            await asyncio.sleep(delay)
            await self.bot.send_message(user_id, message, reply_markup=buttons)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")
        finally:
            # Удаляем задачу из списка
            self._remove_task(user_id, datetime.now() + timedelta(seconds=delay))

    def _remove_task(self, user_id: int, when: datetime):
        """Удаляет задачу из списка запланированных"""
        if user_id in self.scheduled_tasks and when in self.scheduled_tasks[user_id]:
            del self.scheduled_tasks[user_id][when]
            if not self.scheduled_tasks[user_id]:
                del self.scheduled_tasks[user_id]

    def cancel_user_reminders(self, user_id: int):
        """Отменяет все запланированные уведомления для пользователя"""
        if user_id in self.scheduled_tasks:
            for when, task in self.scheduled_tasks[user_id].items():
                task.cancel()
            del self.scheduled_tasks[user_id]

    async def schedule_booking_reminders(self, booking_id: int, date: str, start_time: int,
                                         end_time: int, user_id: int, partner_id: int):
        """Планирует серию напоминаний для бронирования"""
        try:
            # Преобразуем дату и время в объект datetime
            start_dt = datetime.strptime(f"{date} {start_time}:00", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}:00", "%Y-%m-%d %H:%M")

            # Уведомление за 1 час до начала
            remind_start = start_dt - timedelta(hours=1)
            if remind_start > datetime.now():
                user_msg = "⏰ Напоминание: ваша бронь начинается через 1 час!"
                await self.schedule_reminder(remind_start, user_id, user_msg)

                if partner_id:
                    partner_msg = f"⏰ Бронь #{booking_id} начинается через 1 час!"
                    await self.schedule_reminder(remind_start, partner_id, partner_msg)

            # Уведомление за 30 минут до окончания
            remind_end = end_dt - timedelta(minutes=30)
            if remind_end > datetime.now():
                user_msg = "⏳ Ваша бронь заканчивается через 30 минут!"
                await self.schedule_reminder(remind_end, user_id, user_msg)

                if partner_id:
                    partner_msg = f"⏳ Бронь #{booking_id} заканчивается через 30 минут!"
                    await self.schedule_reminder(remind_end, partner_id, partner_msg)

            # Уведомление после окончания
            kb = InlineKeyboardBuilder()
            kb.button(text="⭐ Оставить отзыв", callback_data=f"review_{booking_id}")

            await self.schedule_reminder(
                end_dt + timedelta(minutes=5),
                user_id,
                "✅ Бронь завершена! Спасибо, что выбрали SUPFLOT.",
                kb.as_markup()
            )

        except Exception as e:
            logger.error(f"Ошибка планирования уведомлений для брони #{booking_id}: {e}")