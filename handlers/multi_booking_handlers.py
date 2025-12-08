# handlers/multi_booking_handlers.py

import logging
from functools import partial

from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.NEW_states import BookingState
from keyboards import main_menu
from core.database import Database
from config import WORK_HOURS

logger = logging.getLogger(__name__)
multi_router = Router()


async def select_time_and_ask_quantity(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: Database
):
    await callback.answer()
    start_time = int(callback.data.split("_", 1)[1])
    data = await state.get_data()
    board_id = data["board_id"]
    date     = data["date"]
    duration = data["duration"]

    row = await db.execute(
        "SELECT price, name, total FROM boards WHERE id = ?",
        (board_id,),
        fetch=True
    )
    if not row:
        await callback.message.answer("❌ Ошибка: доска не найдена.", reply_markup=main_menu())
        return
    price, board_name, total_boards = row

    occupied = await db.execute(
        """
        SELECT start_time, duration, quantity
          FROM bookings
         WHERE board_id = ? 
           AND date = ?
           AND status = 'active'
        """,
        (board_id, date),
        fetchall=True
    )
    hour_occupancy = {h: 0 for h in range(WORK_HOURS[0], WORK_HOURS[1])}
    for s, d, qty in occupied:
        for h in range(s, s + d):
            if h in hour_occupancy:
                hour_occupancy[h] += qty

    max_used = max(hour_occupancy[h] for h in range(start_time, start_time + duration))
    free_boards = total_boards - max_used
    if free_boards <= 0:
        await callback.answer("К сожалению, в этом слоте уже нет досок.", show_alert=True)
        return

    max_qty = min(free_boards, 4)

    await state.update_data(
        start_time=start_time,
        price=price,
        board_name=board_name,
        free_boards=free_boards
    )

    builder = InlineKeyboardBuilder()
    for q in range(1, max_qty + 1):
        builder.button(text=str(q), callback_data=f"qty_{q}")
    builder.adjust(4)

    await callback.message.answer(
        f"Сколько досок вы хотите забронировать?\n"
        f"(доступно {free_boards}, не более 4)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingState.select_quantity)


async def process_quantity_and_confirm(
    callback: types.CallbackQuery,
    state: FSMContext,
    db: Database
):
    await callback.answer()
    qty = int(callback.data.split("_", 1)[1])
    data = await state.get_data()

    total_price = data["price"] * data["duration"] * qty
    await state.update_data(quantity=qty, total=total_price)

    end_time = data["start_time"] + data["duration"]
    text = (
        f"Вы выбрали:\n"
        f"🏄 Доска: {data['board_name']}\n"
        f"📅 Дата: {data['date']}\n"
        f"⏰ Время: {data['start_time']:02}:00–{end_time:02}:00\n"
        f"⏳ Длительность: {data['duration']} ч.\n"
        f"📦 Количество: {qty}\n"
        f"💰 Стоимость: <b>{total_price:.2f} ₽</b>\n\n"
        f"Подтвердить бронь?"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отменить",    callback_data="cancel_booking")
    builder.adjust(2)

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await state.set_state(BookingState.confirm_amount)


def register_multi_booking_handlers(router: Router, db: Database):
    router.callback_query(
        StateFilter(BookingState.select_time),
        F.data.startswith("time_")
    )(partial(select_time_and_ask_quantity, db=db))

    router.callback_query(
        StateFilter(BookingState.select_quantity),
        F.data.startswith("qty_")
    )(partial(process_quantity_and_confirm, db=db))


__all__ = ["multi_router", "register_multi_booking_handlers"]
