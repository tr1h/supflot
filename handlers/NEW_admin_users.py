# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter

from keyboards.new_admin_menu import BTN_USERS, new_admin_menu, user_main_menu

logger = logging.getLogger(__name__)
admin_users_router = Router()


class UserFSM(StatesGroup):
    ban_confirm = State()


async def is_admin(db, uid: int) -> bool:
    r = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,), fetch="one")
    return bool(r)


def register_admin_users(router: Router, db):

    @router.message(F.text == BTN_USERS)
    async def show_users(msg: types.Message):
        if not await is_admin(db, msg.from_user.id):
            return await msg.answer("⛔ Нет доступа", reply_markup=user_main_menu())

        rows = await db.execute("""
            SELECT user_id,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(amount),0) AS total
            FROM bookings
            GROUP BY user_id
            ORDER BY total DESC
            LIMIT 30
        """, fetchall=True)

        if not rows:
            return await msg.answer("Пользователей с бронями нет.", reply_markup=new_admin_menu())

        text = "<b>Топ пользователей:</b>\n"
        kb = InlineKeyboardBuilder()
        for uid, cnt, total in rows:
            text += f"👤 <code>{uid}</code> — {cnt} брони, {total:.2f} ₽\n"
            kb.button(text=f"🚫 Бан {uid}", callback_data=f"admin_user_ban:{uid}")
        kb.adjust(2)
        await msg.answer(text, parse_mode="HTML", reply_markup=new_admin_menu())
        await msg.answer("Блокировка (если нужна):", reply_markup=kb.as_markup())

    # Бан
    @router.callback_query(F.data.startswith("admin_user_ban:"))
    async def ban_user_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        uid = int(cq.data.split(":")[1])
        await state.set_state(UserFSM.ban_confirm)
        await state.update_data(uid=uid)

        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, бан", callback_data="admin_user_ban_yes")
        kb.button(text="❌ Отмена",  callback_data="admin_user_ban_no")
        kb.adjust(2)

        await cq.message.answer(f"Забанить пользователя <code>{uid}</code>?", parse_mode="HTML",
                                reply_markup=kb.as_markup())

    @router.callback_query(StateFilter(UserFSM.ban_confirm), F.data == "admin_user_ban_yes")
    async def ban_user_yes(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()
        # простая таблица банов
        await db.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)", commit=True)
        await db.execute("INSERT OR IGNORE INTO banned_users(user_id) VALUES(?)", (data["uid"],), commit=True)
        await state.clear()
        await cq.message.answer("🚫 Пользователь забанен.", reply_markup=new_admin_menu())

    @router.callback_query(StateFilter(UserFSM.ban_confirm), F.data == "admin_user_ban_no")
    async def ban_user_no(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer("Отменено")
        await state.clear()
        await cq.message.answer("Бан отменён.", reply_markup=new_admin_menu())
