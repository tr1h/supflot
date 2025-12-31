# handlers/partner_referral.py
# -*- coding: utf-8 -*-

import re
import logging
from aiogram import Router, Bot, types
from aiogram.filters import Command
from core.database import Database
from config import PLATFORM_COMMISSION_PERCENT
from handlers.partner_cabinet import show_partner_cabinet

logger = logging.getLogger(__name__)

# создаём роутер
router = Router()
# для совместимости с register_partner_referral
referral_router = router

# глобальная переменная для доступа к БД
db: Database = None

def register_partner_referral(dp: Router, database: Database):
    """
    Регистрирует команду /referral и сохраняет объект Database.
    """
    global db
    db = database
    dp.include_router(router)

@router.message(Command("referral"))
async def show_referral_info(msg: types.Message):
    """
    Выдаёт пользователю его реферальную ссылку
    и сразу показывает партнёрский кабинет.
    """
    user_id = msg.from_user.id
    # можно захардкодить или получить динамически через await bot.get_me()
    ref_link = f"https://t.me/supflot_bot?start=ref{user_id}"
    text = (
        "🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"{ref_link}\n\n"
        "Приводите других партнёров и получайте бонусы с их дохода!"
    )
    await msg.answer(text, parse_mode="HTML")
    # сразу открываем партнёрский кабинет
    await show_partner_cabinet(msg, db)

async def patch_partner_table(db_: Database):
    """
    При старте добавляет колонку referrer_id в partners,
    если её нет (для хранения того, кто пригласил).
    """
    rows = await db_.execute("PRAGMA table_info(partners);", fetchall=True)
    cols = [r[1] for r in rows]
    if "referrer_id" not in cols:
        await db_.execute("ALTER TABLE partners ADD COLUMN referrer_id INTEGER", commit=True)
        logger.info("🛠️ Добавлено поле 'referrer_id' в partners")

async def pay_referral_bonus(db_: Database, bot: Bot):
    """
    Проходит по всем credit‑операциям по броням и начисляет
    PLATFORM_COMMISSION_PERCENT% от суммы тому, кто пригласил.
    """
    rows = await db_.execute(
        "SELECT src, amount, partner_id "
        "FROM partner_wallet_ops "
        "WHERE type='credit' AND src LIKE 'booking_%'",
        fetchall=True
    )
    for src, amount, partner_id in rows:
        m = re.match(r"booking_(\d+)", src)
        if not m:
            continue
        booking_id = m.group(1)
        ref_src = f"referral_{booking_id}"

        # пропускаем, если уже начисляли
        if await db_.execute("SELECT 1 FROM partner_wallet_ops WHERE src = ?", (ref_src,), fetch="one"):
            continue

        # кто пригласил этого партнёра?
        row = await db_.execute(
            "SELECT referrer_id FROM partners WHERE id = ?", (partner_id,), fetch="one"
        )
        if not row or not row[0]:
            continue
        referrer_id = row[0]

        bonus = amount * (PLATFORM_COMMISSION_PERCENT / 100.0)

        # сохраняем операцию и уведомляем
        await db_.execute(
            "INSERT INTO partner_wallet_ops(partner_id, type, amount, src) "
            "VALUES(?, 'credit', ?, ?)",
            (referrer_id, bonus, ref_src),
            commit=True
        )
        try:
            await bot.send_message(
                chat_id=referrer_id,
                text=f"💵 Вам начислен реферальный бонус {bonus:.2f}₽ за бронь #{booking_id}"
            )
        except Exception:
            logger.exception(f"Не удалось уведомить реферера {referrer_id}")
