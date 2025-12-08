# run_bot.py
# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import signal
import time
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import BotCommand

from config import BOT_TOKEN, PLATFORM_COMMISSION_PERCENT
from core.database import Database
from core.schema import init_db
from core.seed import seed_dev_data

# ─── handlers ──────────────────────────────────────────────────────────────
from handlers.user_cabinet import register_user_cabinet, user_cabinet_router
from handlers.daily_handlers import daily_router
from handlers.partner_handlers import register_partner_handlers, partner_router
from handlers.catalog_handlers import catalog_router
from handlers.review_handlers import review_router, register_review_handlers
from handlers.multi_booking_handlers import register_multi_booking_handlers, multi_router
from handlers.choose_location import register_choose_location_handlers, choose_location_router
from handlers.NEW_user_bundle import register_user_handlers
from handlers.partner_fsm_handlers import register_partner_fsm_handlers
from handlers.partner_cabinet import register_partner_cabinet
from handlers.NEW_daily_booking_p2p import register_daily_booking, daily_booking_p2p_router
from handlers.NEW_payments import register_payment_handlers
from handlers.NEW_admin_bundle import register_all_admin_handlers

# ─── финансы & кошелёк ─────────────────────────────────────────────────────
from handlers.finance_handlers import register_finance_handlers
from handlers.PARTNER_wallet.earnings import register_earnings_handlers
from handlers.PARTNER_wallet.wallet_handlers import register_wallet_handlers
from handlers.PARTNER_wallet.withdraw_handlers import register_withdraw_handlers
from handlers.admin_withdraw_handlers import register_admin_withdraw

# ─── misc: Помощь, Контакты, Оферта ─────────────────────────────────────────
from handlers.misc_handlers import router as misc_router


# ─── логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"),
              logging.StreamHandler()]
)
logging.getLogger("aiogram").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


# ─── Авто-завершение просроченных броней ────────────────────────────────────
async def complete_and_pay_once(db: Database, bot: Bot):
    """
    Завершаем все активные брони, у которых NOW >= (date + start_time:start_minute + duration_minutes).
    Начисление партнёру делаем ТОЛЬКО для не-telegram оплат (чтобы не задвоить).
    """
    # Берём кандидатов с датой не позже сегодня — остальное считаем в Python
    rows = await db.execute(
        """
        SELECT bk.id, bk.date, bk.start_time, bk.start_minute, bk.duration,
               COALESCE(bk.payment_method,''), bk.amount,
               b.partner_id
          FROM bookings bk
          JOIN boards b ON b.id = bk.board_id
         WHERE bk.status = 'active'
           AND date(bk.date) <= date('now','localtime')
        """,
        fetchall=True
    )
    if not rows:
        return

    now = datetime.now()
    for (booking_id, date_str, sh, sm, duration_min,
         pay_method, amount, partner_id) in rows:

        try:
            start_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
                hour=int(sh or 0), minute=int(sm or 0), second=0, microsecond=0
            )
        except Exception:
            # Если вдруг в базе иной формат — подстрахуемся
            try:
                start_dt = datetime.fromisoformat(date_str).replace(
                    hour=int(sh or 0), minute=int(sm or 0), second=0, microsecond=0
                )
            except Exception:
                log.warning(f"Skip booking #{booking_id}: bad date format {date_str!r}")
                continue

        end_dt = start_dt + timedelta(minutes=int(duration_min or 0))
        if now >= end_dt:
            # 1) Завершаем
            await db.execute(
                "UPDATE bookings SET status='completed' WHERE id = ?",
                (booking_id,),
                commit=True
            )
            # 2) Начисляем ТОЛЬКО если не telegram
            if (pay_method or "").lower() != "telegram":
                share = float(amount) * (1 - PLATFORM_COMMISSION_PERCENT / 100.0)
                await db.execute(
                    """
                    INSERT INTO partner_wallet_ops(
                      partner_id, type, amount, src, created_at
                    ) VALUES (
                      ?, 'credit', ?, 'booking_completed',
                      datetime('now','localtime')
                    )
                    """,
                    (partner_id, share),
                    commit=True
                )


async def auto_complete_and_pay(db: Database, bot: Bot, stop_event: asyncio.Event):
    while not stop_event.is_set():
        log.info("▶️ Фон: авто-завершение броней…")
        try:
            await complete_and_pay_once(db, bot)
        except Exception:
            log.exception("Ошибка в complete_and_pay_once")
        # ждём 60с или остановку
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass


# ─── Middleware и глобальная обработка ошибок ───────────────────────────────
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        started = time.time()
        try:
            result = await handler(event, data)
            return result
        finally:
            elapsed = (time.time() - started) * 1000
            name = getattr(handler, "__name__", handler.__class__.__name__)
            logging.getLogger(__name__).info(f"{name} → {elapsed:.0f}ms")


async def global_error_handler(update: types.Update, exception: Exception = None) -> bool:
    log.exception("Unhandled error: %r", exception)
    # Пытаемся ответить туда, откуда пришло событие
    target = None
    if update.message:
        target = update.message
    elif update.callback_query:
        target = update.callback_query.message
    if target:
        try:
            await target.answer("❌ Внутренняя ошибка, попробуйте позже.")
        except Exception:
            pass
    return True


# ─── MAIN ────────────────────────────────────────────────────────────────
async def main():
    token = BOT_TOKEN or os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан")

    # инициализируем бота и диспетчера
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    dp.errors.register(global_error_handler)

    # инициализация БД
    db = Database()
    bot.db = db  # если где-то ожидают bot.db
    await init_db(db)
    await seed_dev_data(db)  # 🔁 убрать в проде

    # единоразовое завершение + запуск фонового цикла с управляемой остановкой
    await complete_and_pay_once(db, bot)
    stop_event = asyncio.Event()
    background_task = asyncio.create_task(auto_complete_and_pay(db, bot, stop_event))

    # настраиваем команды
    await bot.set_my_commands([
        BotCommand(command="start",    description="Начать"),
        BotCommand(command="help",     description="Помощь"),
        BotCommand(command="daily",    description="Суточная аренда"),
        BotCommand(command="partner",  description="Партнёрская панель"),
        BotCommand(command="contacts", description="Контакты"),
        BotCommand(command="offer",    description="Оферта"),
        BotCommand(command="admin",    description="Админ-панель"),
    ])

    # ── порядок регистрации: сначала платежи/пользовательские, потом админские ──
    # партнёрские FSM и кабинеты
    register_partner_fsm_handlers(dp, db)
    register_partner_cabinet(dp, db)
    register_wallet_handlers(dp, db)
    register_withdraw_handlers(dp, db)
    register_admin_withdraw(dp, db)

    # пользовательский кабинет
    register_user_cabinet(user_cabinet_router, db)
    dp.include_router(user_cabinet_router)

    # обычные флоу
    dp.include_router(daily_router)
    register_partner_handlers(partner_router, db)
    dp.include_router(partner_router)

    # новый пользовательский бандл (включая выбор типа брони)
    new_user_router = Router()
    register_user_handlers(new_user_router, db)
    dp.include_router(new_user_router)

    # публичный каталог/отзывы/мультибронь/суточная p2p
    dp.include_router(catalog_router)
    register_review_handlers(dp, db)
    dp.include_router(review_router)

    register_multi_booking_handlers(multi_router, db)
    dp.include_router(multi_router)

    register_daily_booking(daily_booking_p2p_router, db)
    dp.include_router(daily_booking_p2p_router)

    # финансы и платежи — ВАЖНО: платежи подключаем ДО админских роутеров
    register_finance_handlers(dp, db)
    register_payment_handlers(dp, db)
    register_earnings_handlers(dp, db)

    # разное
    dp.include_router(misc_router)

    # админский бандл в самом конце
    admin_router = Router()
    register_all_admin_handlers(admin_router, db, bot)
    dp.include_router(admin_router)

    register_choose_location_handlers(choose_location_router, db)
    dp.include_router(choose_location_router)

    # корректное завершение по сигналам
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Windows/IDE — просто игнор
            pass

    try:
        await dp.start_polling(bot)
    finally:
        # Останавливаем фон и закрываем ресурсы
        stop_event.set()
        try:
            await asyncio.wait_for(background_task, timeout=3)
        except Exception:
            background_task.cancel()
        try:
            await db.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
