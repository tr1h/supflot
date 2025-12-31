# handlers/NEW_admin_main.py
# -*- coding: utf-8 -*-
from aiogram import Router, types, F
from aiogram.filters import Command

from handlers.finance_handlers import get_finance_stats, format_finance_stats
from keyboards.new_admin_menu import (
    new_admin_menu, new_finance_menu, user_main_menu,
    BTN_FINANCE, BTN_BACK
)

admin_main_router = Router()


def register_admin_main(router: Router, db):

    async def is_admin(uid: int) -> bool:
        row = await db.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (uid,), fetch="one"
        )
        return bool(row)

    @router.message(Command("admin"))
    async def admin_entry(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Доступ запрещён!", reply_markup=user_main_menu())
        await msg.answer("👑 Админ‑панель:", reply_markup=new_admin_menu())

    # 📈 Финансы
    @router.message(F.text == BTN_FINANCE)
    async def show_finances(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Нет доступа.", reply_markup=user_main_menu())
        stats = await get_finance_stats(db)
        await msg.answer(
            format_finance_stats(stats, "— вся история"),
            reply_markup=new_finance_menu()
        )

    # ⬅️ Назад
    @router.message(F.text == BTN_BACK)
    async def back_to_admin_menu(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Нет доступа.", reply_markup=user_main_menu())
        await msg.answer("🔙 Назад в админ‑панель", reply_markup=new_admin_menu())
