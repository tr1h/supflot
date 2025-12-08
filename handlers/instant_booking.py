# handlers/instant_booking.py
# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F, Bot, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.NEW_states import NewBookingChoice, BookingState
from keyboards.common import confirm_booking_keyboard, payment_choice_keyboard, main_menu
from handlers.NEW_utils import ensure_common_tables, save_booking_and_decrease

__all__ = ["register_instant_booking"]

class InstantFlow(StatesGroup):
    choosing_location = State()
    select_board     = State()
    select_duration  = State()
    confirm          = State()

def register_instant_booking(router: Router, db):
    @router.callback_query(NewBookingChoice.choosing_mode, F.data == "mode:instant")
    async def inst_start(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        await ensure_common_tables(db)

        locs = await db.execute(
            """
            SELECT DISTINCT l.id, l.name
            FROM locations l
            JOIN boards b ON b.location_id = l.id
            WHERE b.quantity > 0
              AND b.is_active = 1
              AND l.is_active = 1
            ORDER BY l.name
            """,
            fetchall=True
        )
        if not locs:
            return await cq.message.answer("❌ Нет доступных локаций.", reply_markup=main_menu())

        kb = InlineKeyboardBuilder()
        for lid, lname in locs:
            kb.button(text=lname, callback_data=f"loc_{lid}")
        kb.adjust(1)

        await cq.message.answer("Выберите локацию:", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.choosing_location)

    @router.callback_query(InstantFlow.choosing_location, F.data.startswith("loc_"))
    async def inst_choose_loc(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        loc_id = int(cq.data.split("_", 1)[1])
        await state.update_data(location_id=loc_id)

        rows = await db.execute(
            """
            SELECT id, name, price, quantity
            FROM boards
            WHERE location_id = ?
              AND quantity > 0
              AND is_active = 1
            ORDER BY name
            """,
            (loc_id,), fetchall=True
        )
        if not rows:
            return await cq.answer("❌ Нет досок в этой локации.", show_alert=True)

        kb = InlineKeyboardBuilder()
        for bid, name, price, qty in rows:
            kb.button(text=f"{name} — {price}₽/ч ({qty})", callback_data=f"inst_{bid}")
        kb.adjust(1)

        await cq.message.answer("Выберите доску:", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.select_board)

    @router.callback_query(InstantFlow.select_board, F.data.startswith("inst_"))
    async def inst_select_board(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split("_", 1)[1])
        await state.update_data(board_id=bid)

        row = await db.execute("SELECT name, price FROM boards WHERE id = ?", (bid,), fetch="one")
        if not row:
            return await cq.message.answer("❌ Доска не найдена.")
        name, price = row
        await state.update_data(board_name=name, price=price)

        kb = InlineKeyboardBuilder()
        for m in [30, 60, 120, 180]:
            txt = f"{m} мин" if m < 60 else f"{m//60} ч"
            kb.button(text=txt, callback_data=f"dur_{m}")
        kb.adjust(4)

        await cq.message.answer("На сколько минут?", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.select_duration)

    @router.callback_query(InstantFlow.select_duration, F.data.startswith("dur_"))
    async def inst_select_duration(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        m = int(cq.data.split("_", 1)[1])
        data = await state.get_data()

        now = datetime.now()
        start_dt = (now + timedelta(minutes=5)).replace(second=0, microsecond=0)
        end_dt   = start_dt + timedelta(minutes=m)
        amount   = round(data["price"] * (m / 60), 2)

        await state.update_data(
            date=start_dt.date().isoformat(),
            start_time=start_dt.hour,
            start_minute=start_dt.minute,
            duration=m,
            quantity=1,
            amount=amount
        )

        await cq.message.answer(
            f"🛶 {data['board_name']}\n"
            f"📅 {start_dt:%H:%M}–{end_dt:%H:%M}\n"
            f"⏳ {m} мин | 💰 {amount:.2f}₽",
            reply_markup=confirm_booking_keyboard()
        )
        await state.set_state(InstantFlow.confirm)

        delay = (start_dt - now - timedelta(minutes=5)).total_seconds()
        if delay > 0:
            asyncio.create_task(_remind_start(cq.from_user.id, data["board_name"], delay))

    async def _remind_start(user_id: int, board_name: str, delay: float):
        await asyncio.sleep(delay)
        await Bot.get_current().send_message(user_id, f"⏰ Через 5 мин аренда: {board_name}")

    @router.callback_query(InstantFlow.confirm, F.data == "confirm_booking")
    async def inst_confirm(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()

        # вот здесь ровно три аргумента:
        await save_booking_and_decrease(db, cq.from_user.id, data)

        await state.set_state(BookingState.select_payment)
        await cq.message.answer("Выберите способ оплаты:", reply_markup=payment_choice_keyboard())

    @router.callback_query(F.data == "cancel_booking")
    async def inst_cancel(cq: CallbackQuery, state: FSMContext):
        await cq.answer("❌ Отменена.")
        await cq.message.answer("❌ Бронь отменена.", reply_markup=main_menu())
        await state.clear()
