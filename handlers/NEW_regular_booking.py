# -*- coding: utf-8 -*-
"""
Классическая бронь по дате/времени.

Потоки:
- выбор локации -> доски -> даты -> времени -> длительности -> количества -> подтверждение
- после подтверждения переходим к выбору оплаты (Telegram / карта вручную / нал)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.NEW_states import BookingState
from keyboards.common import (
    confirm_booking_keyboard,
    payment_choice_keyboard,
    main_menu,
)
from handlers.NEW_utils import ensure_common_tables

__all__ = ["register_regular_booking", "start_regular_booking"]

_DB = None  # будет установлен при регистрации


def _hm(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


def register_regular_booking(router: Router, db):
    """Регистрируем хендлеры и привязываем БД к модулю."""
    global _DB
    _DB = db

    # ───────────── Старт из инлайна: Выбор локации ─────────────
    @router.callback_query(StateFilter(BookingState.select_location), F.data.startswith("reg_loc:"))
    async def reg_pick_location(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        loc_id = int(cq.data.split(":", 1)[1])
        await state.update_data(location_id=loc_id)

        boards = await _DB.execute(
            """
            SELECT id, name, price, COALESCE(quantity,total,0) as avail
              FROM boards
             WHERE location_id = ?
               AND (is_active = 1 OR is_active IS NULL)
               AND COALESCE(quantity,total,0) > 0
             ORDER BY name
            """,
            (loc_id,), fetchall=True
        )
        if not boards:
            return await cq.message.answer("❌ В этой локации нет доступных досок.")

        kb = InlineKeyboardBuilder()
        for bid, name, price, avail in boards:
            kb.button(text=f"{name} — {int(price)}₽/ч (своб. {avail})", callback_data=f"reg_board:{bid}")
        kb.adjust(1)
        await cq.message.edit_text("Выберите доску:", reply_markup=kb.as_markup())
        await state.set_state(BookingState.select_board)

    # ───────────── Доска → Дата ─────────────
    @router.callback_query(StateFilter(BookingState.select_board), F.data.startswith("reg_board:"))
    async def reg_pick_board(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split(":", 1)[1])

        row = await _DB.execute(
            "SELECT name, price, COALESCE(quantity,total,0) FROM boards WHERE id = ?",
            (bid,), fetch="one"
        )
        if not row:
            return await cq.message.answer("❌ Доска не найдена.")

        name, price, avail = row
        await state.update_data(board_id=bid, board_name=name, price=float(price), max_avail=int(avail))

        # 7 ближайших дней
        today = datetime.now().date()
        kb = InlineKeyboardBuilder()
        for i in range(7):
            d = today + timedelta(days=i)
            label = d.strftime("%d.%m (%a)")
            kb.button(text=label, callback_data=f"reg_date:{d.isoformat()}")
        kb.adjust(3, 4)
        await cq.message.edit_text("Дата аренды:", reply_markup=kb.as_markup())
        await state.set_state(BookingState.select_date)

    # ───────────── Дата → Время ─────────────
    @router.callback_query(StateFilter(BookingState.select_date), F.data.startswith("reg_date:"))
    async def reg_pick_date(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        date_iso = cq.data.split(":", 1)[1]
        await state.update_data(date=date_iso)

        # Слоты каждые 30 минут с 08:00 до 20:00
        kb = InlineKeyboardBuilder()
        for h in range(8, 21):
            for m in (0, 30):
                kb.button(text=_hm(h, m), callback_data=f"reg_time:{h:02d}:{m:02d}")
        kb.adjust(6)
        await cq.message.edit_text("Время начала:", reply_markup=kb.as_markup())
        await state.set_state(BookingState.select_time)

    # ───────────── Время → Длительность ─────────────
    @router.callback_query(StateFilter(BookingState.select_time), F.data.startswith("reg_time:"))
    async def reg_pick_time(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        hm = cq.data.split(":", 1)[1]  # "HH:MM"
        h, m = map(int, hm.split(":"))
        await state.update_data(start_time=h, start_minute=m)

        kb = InlineKeyboardBuilder()
        for minutes in (60, 120, 180, 240):
            kb.button(
                text=(f"{minutes//60} ч"),
                callback_data=f"reg_dur:{minutes}"
            )
        kb.adjust(4)
        await cq.message.edit_text("Длительность:", reply_markup=kb.as_markup())
        await state.set_state(BookingState.select_duration)

    # ───────────── Длительность → Количество ─────────────
    @router.callback_query(StateFilter(BookingState.select_duration), F.data.startswith("reg_dur:"))
    async def reg_pick_duration(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        minutes = int(cq.data.split(":", 1)[1])
        await state.update_data(duration=minutes)

        data = await state.get_data()
        max_q = max(1, min(5, int(data.get("max_avail", 1))))

        kb = InlineKeyboardBuilder()
        for q in range(1, max_q + 1):
            kb.button(text=str(q), callback_data=f"reg_qty:{q}")
        kb.adjust(5)
        await cq.message.edit_text("Количество досок:", reply_markup=kb.as_markup())
        await state.set_state(BookingState.select_quantity)

    # ───────────── Количество → Подтверждение ─────────────
    @router.callback_query(StateFilter(BookingState.select_quantity), F.data.startswith("reg_qty:"))
    async def reg_pick_quantity(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        qty = int(cq.data.split(":", 1)[1])

        data = await state.update_data(quantity=qty) or await state.get_data()

        price   = float(data["price"])
        minutes = int(data["duration"])
        amount  = round(price * (minutes / 60.0) * qty, 2)

        start_h = int(data.get("start_time", 0))
        start_m = int(data.get("start_minute", 0))
        date_iso = data["date"]
        start_dt = datetime.fromisoformat(date_iso)  # полночь этого дня
        start_dt = start_dt.replace(hour=start_h, minute=start_m)

        end_dt = start_dt + timedelta(minutes=minutes)

        await state.update_data(amount=amount)

        text = (
            "📝 Проверьте бронь:\n\n"
            f"📍 Дата: {date_iso}\n"
            f"🕒 Время: {_hm(start_h, start_m)}–{end_dt.strftime('%H:%M')}\n"
            f"🛶 Доска: {data['board_name']} × {qty}\n"
            f"⏳ Длительность: {minutes//60} ч\n"
            f"💰 Сумма: {amount:.2f} ₽"
        )
        await cq.message.edit_text(text, reply_markup=confirm_booking_keyboard())
        await state.set_state(BookingState.confirm_amount)

    # ───────────── Подтверждение → Способ оплаты ─────────────
    @router.callback_query(StateFilter(BookingState.confirm_amount), F.data == "confirm_booking")
    async def reg_confirm(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        # НИЧЕГО в БД тут не пишем — запись создадут платежные хендлеры.
        await state.set_state(BookingState.select_payment)
        await cq.message.edit_text("Выберите способ оплаты:", reply_markup=payment_choice_keyboard())

    # Отмена
    @router.callback_query(F.data == "cancel_booking")
    async def reg_cancel(cq: CallbackQuery, state: FSMContext):
        await cq.answer("❌ Отменено.", show_alert=True)
        await cq.message.edit_text("Отменено.", reply_markup=main_menu())
        await state.clear()


async def start_regular_booking(message: Message, state: FSMContext, db=None):
    """
    Старт потока «Классическая бронь» — совместимо со старым вызовом:
    start_regular_booking(message, state, db)
    """
    global _DB
    if db is not None:
        _DB = db
    if _DB is None:
        # если забыли вызвать register_regular_booking до старта
        raise RuntimeError("register_regular_booking(router, db) не был вызван раньше")

    # убедимся, что базовые таблицы есть
    await ensure_common_tables(_DB)

    # список локаций, где есть активные доски
    locs = await _DB.execute(
        """
        SELECT DISTINCT l.id, l.name
          FROM locations l
          JOIN boards b ON b.location_id = l.id
         WHERE (l.is_active = 1 OR l.is_active IS NULL)
           AND (b.is_active = 1 OR b.is_active IS NULL)
           AND COALESCE(b.quantity, b.total, 0) > 0
         ORDER BY l.name
        """,
        fetchall=True
    )

    if not locs:
        return await message.answer("❌ Сейчас нет доступных локаций.", reply_markup=main_menu())

    kb = InlineKeyboardBuilder()
    for lid, lname in locs:
        kb.button(text=lname, callback_data=f"reg_loc:{lid}")
    kb.adjust(1)

    await message.answer("Выберите локацию:", reply_markup=kb.as_markup())
    await state.set_state(BookingState.select_location)
