# handlers/NEW_admin_finance.py
# -*- coding: utf-8 -*-
"""
Админ: раздел «Финансы».
Показывает агрегированную статистику (доход, расходы, прибыль и т.д.).
"""

from datetime import datetime, timedelta
from aiogram import Router, types, F

from handlers.finance_handlers import get_finance_stats, format_finance_stats
from keyboards import new_finance_menu as finance_menu
from keyboards import new_main_menu as main_menu

admin_finance_router = Router()


def register_admin_finance(router: Router, db):

    async def is_admin(user_id: int) -> bool:
        row = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetch="one")
        return row is not None

    # Кнопка «📈 Финансы» (общая статистика за весь период)
    @router.message(F.text == "📈 Финансы")
    async def show_finances(message: types.Message):
        if not await is_admin(message.from_user.id):
            return await message.answer("⛔ Доступ запрещён!", reply_markup=main_menu())

        stats = await get_finance_stats(db)
        await message.answer(format_finance_stats(stats), reply_markup=finance_menu())

    # Пример дополнительных кнопок (если нужны):
    @router.message(F.text == "💵 Оборот сегодня")
    async def finances_today(message: types.Message):
        if not await is_admin(message.from_user.id):
            return await message.answer("⛔ Доступ запрещён!", reply_markup=main_menu())
        today = datetime.now().date().isoformat()
        stats = await get_finance_stats(db, today, today)
        await message.answer(format_finance_stats(stats, "за сегодня"), reply_markup=finance_menu())

    @router.message(F.text == "📅 За месяц")
    async def finances_month(message: types.Message):
        if not await is_admin(message.from_user.id):
            return await message.answer("⛔ Доступ запрещён!", reply_markup=main_menu())
        today = datetime.now().date()
        first = today.replace(day=1).isoformat()
        stats = await get_finance_stats(db, first, today.isoformat())
        await message.answer(format_finance_stats(stats, "за месяц"), reply_markup=finance_menu())


__all__ = ["register_admin_finance", "admin_finance_router"]
