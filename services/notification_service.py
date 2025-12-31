# services/notification_service.py

from aiogram import Bot

from handlers.admin_notifications import notify_admins as send_admin_notification

class NotificationService:
    @staticmethod
    async def new_booking(bot: Bot, booking_id: int, summary_text: str):
        """
        Уведомляет администраторов о новой броне.
        Делегирует существующему notify_admins из админского модуля.
        """
        await send_admin_notification(booking_id, summary_text, bot)

    @staticmethod
    def schedule_reminder(user_id: int, run_at, message: str):
        """
        Планирует однократное напоминание пользователю.
        Заглушка: пока не интегрирован automations, можно оставить пустой.
        """
        # Здесь можно реализовать через automations.create(...)
        pass
