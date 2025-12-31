# notifications/notification_triggers.py
import logging
from aiogram import Bot
from core.database import Database
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Диспетчер событий для уведомлений"""

    def __init__(self):
        self.booking_created = Event()
        self.booking_confirmed = Event()
        self.booking_canceled = Event()
        self.payment_processed = Event()
        self.withdraw_requested = Event()


class Event:
    """Класс события"""

    def __init__(self):
        self.handlers = []

    def register(self, handler):
        self.handlers.append(handler)

    async def trigger(self, *args, **kwargs):
        for handler in self.handlers:
            try:
                await handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка обработчика события: {e}", exc_info=True)


async def setup_notification_triggers(event_dispatcher: EventDispatcher, notification_service: NotificationService):
    """Настройка триггеров уведомлений"""
    event_dispatcher.booking_created.register(notification_service.notify_new_booking)
    event_dispatcher.booking_confirmed.register(notification_service.notify_booking_confirmation)
    event_dispatcher.booking_canceled.register(notification_service.cancel_booking_notifications)
    event_dispatcher.payment_processed.register(notification_service.notify_payment)
    event_dispatcher.withdraw_requested.register(notification_service.notify_withdraw_request)

    return notification_service