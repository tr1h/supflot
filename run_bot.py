"""Точка входа для запуска бота"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import Config
from core.database import Database
from core.schema import init_db
from core.seed import seed_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    # Валидация конфигурации
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Инициализация базы данных
    db = Database()
    try:
        await db.connect()
        await init_db(db)
        await seed_db(db)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return
    
    # Инициализация бота
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрация обработчиков
    from handlers.user_handlers import register_user_handlers
    from handlers.booking_handlers import register_booking_handlers
    from handlers.payment_handlers import register_payment_handlers
    from handlers.admin_handlers import register_admin_handlers
    from handlers.user_bookings_handlers import register_user_bookings_handlers
    from aiogram import Router
    
    router = Router()
    from handlers.partner_handlers import register_partner_handlers
    from handlers.partner_wallet_handlers import register_partner_wallet_handlers
    
    # Создаем notification_service для передачи в обработчики
    from notifications.notification_service import NotificationService
    notification_service = NotificationService(bot, db)
    
    from handlers.partner_registration_handlers import register_partner_registration_handlers
    from handlers.review_handlers import register_review_handlers
    from handlers.catalog_handlers import register_catalog_handlers
    from handlers.profile_handlers import register_profile_handlers
    from handlers.multi_booking_handlers import register_multi_booking_handlers
    
    register_user_handlers(router, db)
    register_booking_handlers(router, db, bot)
    register_payment_handlers(router, db, bot, notification_service)
    register_admin_handlers(router, db, bot, notification_service)
    register_user_bookings_handlers(router, db)
    register_partner_handlers(router, db, bot, notification_service)
    register_partner_wallet_handlers(router, db)
    register_partner_registration_handlers(router, db, bot, notification_service)
    register_review_handlers(router, db, bot)
    register_catalog_handlers(router, db, bot)
    register_profile_handlers(router, db, bot)
    register_multi_booking_handlers(router, db, bot)
    
    # Обработчик необработанных callback_query (должен быть последним)
    @router.callback_query()
    async def unhandled_callback(callback_query: CallbackQuery):
        """Логирование необработанных callback_query"""
        logger.warning(f"Unhandled callback_query: {callback_query.data} from user {callback_query.from_user.id}")
        try:
            await callback_query.answer("⚠️ Эта функция пока не реализована", show_alert=True)
        except:
            pass
    
    dp.include_router(router)
    
    # Запуск планировщика уведомлений
    from notifications.notification_scheduler import NotificationScheduler
    scheduler = NotificationScheduler(db, bot)
    scheduler_task = asyncio.create_task(scheduler.start())
    
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await scheduler.stop()
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

