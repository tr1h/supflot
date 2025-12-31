# handlers/finance_menu.py
from aiogram import Router, types, F

from keyboards.new_admin_menu import new_finance_menu as admin_finance_menu
from keyboards.new_partner_menu import partner_finance_menu  # создадим ниже
from keyboards import main_menu

from handlers.finance_handlers import get_finance_stats, format_finance_stats
from helpers.wallet import get_partner_balance

from datetime import datetime

finance_router = Router()

def register_finance_menu(router: Router, db):
    router.include_router(finance_router)

    async def is_admin(user_id: int) -> bool:
        row = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetch="one")
        return row is not None

    # Универсальный обработчик
    @finance_router.message(F.text == "📈 Финансы")
    async def finance_menu(msg: types.Message):
        user_id = msg.from_user.id
        if await is_admin(user_id):
            # 👨‍💼 Меню администратора
            stats = await get_finance_stats(db)
            return await msg.answer(format_finance_stats(stats), reply_markup=admin_finance_menu())
        else:
            # 👥 Меню партнёра
            balance = await get_partner_balance(db, user_id)
            return await msg.answer(
                f"💼 Ваш доход: {balance:.2f} ₽", reply_markup=partner_finance_menu()
            )

    # Доп. обработчики — админские
    @finance_router.message(F.text == "💵 Оборот сегодня")
    async def today(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Доступ запрещён", reply_markup=main_menu())
        today = datetime.now().date().isoformat()
        stats = await get_finance_stats(db, today, today)
        await msg.answer(format_finance_stats(stats, "за сегодня"), reply_markup=admin_finance_menu())

    @finance_router.message(F.text == "📅 За месяц")
    async def this_month(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Доступ запрещён", reply_markup=main_menu())
        today = datetime.now().date()
        first_day = today.replace(day=1).isoformat()
        stats = await get_finance_stats(db, first_day, today.isoformat())
        await msg.answer(format_finance_stats(stats, "за месяц"), reply_markup=admin_finance_menu())
