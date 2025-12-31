# handlers/PARTNER_wallet/referral_handlers.py
# -*- coding: utf-8 -*-

from aiogram import Router, types
from aiogram.filters import Command

from handlers.partner_cabinet import show_partner_cabinet  # показываем полноценный кабинет
from core.database import Database

referral_router = Router()

def register_referral_handlers(dp: Router, db: Database):
    # Сохраняем доступ к БД
    referral_router.data["db"] = db
    dp.include_router(referral_router)

@referral_router.message(Command("referral"))
async def show_referral_info(msg: types.Message):
    db: Database = referral_router.data["db"]
    user_id = msg.from_user.id
    ref_link = f"https://t.me/@supflot_bot?start=ref{user_id}"
    text = (
        "🔗 Ваша реферальная ссылка:\n"
        f"{ref_link}\n\n"
        "Приводите других партнёров и получайте % с их дохода!"
    )
    # Сначала показываем ссылку
    await msg.answer(text)
    # Затем выводим полноценный партнёрский кабинет
    await show_partner_cabinet(msg, db)
