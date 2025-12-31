# -*- coding: utf-8 -*-
"""
Суточная аренда (P2P) — без привязки к локации.
"""

from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import payment_choice_keyboard, main_menu
from handlers.NEW_states import BookingState

daily_booking_p2p_router = Router()


class DailyP2PFlow(StatesGroup):
    choosing_board = State()
    choosing_start_date = State()
    choosing_days = State()


async def start_daily_booking_flow(msg: Message, state: FSMContext, db):
    """
    Универсальная точка входа в P2P аренду (из любой кнопки).
    """
    await state.clear()
    rows = await db.execute(
        "SELECT id, name, daily_price, address FROM daily_boards WHERE is_active = 1 AND available_quantity > 0",
        fetchall=True
    )
    if not rows:
        return await msg.answer("❌ Нет доступных досок.", reply_markup=main_menu())

    kb = InlineKeyboardBuilder()
    for bid, name, price, addr in rows:
        kb.button(text=f"{name} — {price}₽", callback_data=f"dpboard_{bid}")
    kb.adjust(1)
    await msg.answer("Выберите доску для суточной аренды:", reply_markup=kb.as_markup())
    await state.set_state(DailyP2PFlow.choosing_board)


def register_daily_booking(router: Router, db):
    @router.message(F.text == "📆 Суточная аренда")
    async def start_p2p_daily(msg: Message, state: FSMContext):
        await start_daily_booking_flow(msg, state, db)

    @router.callback_query(DailyP2PFlow.choosing_board, F.data.startswith("dpboard_"))
    async def select_p2p_board(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        board_id = int(cq.data.split("_", 1)[1])
        row = await db.execute(
            "SELECT name, daily_price, address FROM daily_boards WHERE id = ?",
            (board_id,), fetch=True
        )
        if not row:
            return await cq.message.answer("❌ Доска не найдена.")
        name, price, address = row
        await state.update_data(board_id=board_id, board_name=name, price=price, address=address)

        today = datetime.now().date()
        kb = InlineKeyboardBuilder()
        for i in range(7):
            d = today + timedelta(days=i)
            kb.button(text=d.strftime("%a %d.%m"), callback_data=f"dpdate_{d.isoformat()}")
        kb.adjust(3)
        await cq.message.answer("📅 Выберите дату начала:", reply_markup=kb.as_markup())
        await state.set_state(DailyP2PFlow.choosing_start_date)

    @router.callback_query(DailyP2PFlow.choosing_start_date, F.data.startswith("dpdate_"))
    async def select_start_date(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        start_date = cq.data.split("_", 1)[1]
        await state.update_data(start_date=start_date)

        kb = InlineKeyboardBuilder()
        for d in range(1, 8):
            kb.button(text=f"{d} сут", callback_data=f"dpdays_{d}")
        kb.adjust(4)
        await cq.message.answer("⏳ Укажите срок аренды:", reply_markup=kb.as_markup())
        await state.set_state(DailyP2PFlow.choosing_days)

    @router.callback_query(DailyP2PFlow.choosing_days, F.data.startswith("dpdays_"))
    async def select_days(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        days = int(cq.data.split("_", 1)[1])
        await state.update_data(days=days)

        data = await state.get_data()
        start = datetime.fromisoformat(data["start_date"])
        end = start + timedelta(days=days)
        amount = data["price"] * days
        await state.update_data(amount=amount)

        await cq.message.answer(
            f"📝 Подтвердите аренду:\n\n"
            f"🛶 {data['board_name']}\n"
            f"📅 {start.strftime('%d.%m')} – {end.strftime('%d.%m')} ({days} суток)\n"
            f"📍 Адрес: {data['address']}\n"
            f"💰 {amount:.0f} ₽",
            reply_markup=payment_choice_keyboard()
        )

        # unified оплата (добавим в бронирование)
        await state.update_data(
            date=start.strftime("%Y-%m-%d"),
            start_time=0,
            start_minute=0,
            duration=days * 24,
            quantity=1
        )
        await state.set_state(BookingState.select_payment)


__all__ = [
    "daily_booking_p2p_router",
    "register_daily_booking",
    "start_daily_booking_flow"
]
