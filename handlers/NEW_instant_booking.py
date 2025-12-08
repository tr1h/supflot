# handlers/NEW_instant_booking.py
# -*- coding: utf-8 -*-
"""
Мгновенная бронь («у воды»).

Функционал:
- выбор локации / доски / количества / длительности
- подтверждение и выбор оплаты (карта/нал/телеграм-инвойс)
- запись в bookings + уменьшение boards.quantity
- напоминание за 5 минут
- уведомление партнёру
"""

import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter

from handlers.NEW_states import NewBookingChoice, BookingState
from keyboards.common import (
    confirm_booking_keyboard,
    payment_choice_keyboard,
    main_menu,
)

from handlers.NEW_utils import (
    ensure_common_tables,
    notify_partner,
)

__all__ = ["register_instant_booking", "start_instant_booking"]


class InstantFlow(StatesGroup):
    choosing_location = State()
    select_board      = State()
    select_quantity   = State()
    select_duration   = State()
    confirm           = State()


async def _ensure_instant_table(db):
    # отдельная табличка на будущее (аналитика мгновенных), сейчас не обязательна
    await db.execute("""
        CREATE TABLE IF NOT EXISTS partner_instant_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            board_id INTEGER NOT NULL,
            board_name TEXT NOT NULL,
            date DATE NOT NULL,
            start_time INTEGER NOT NULL,
            start_minute INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            amount REAL NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, commit=True)


async def start_instant_booking(msg: Message, state: FSMContext, db):
    """
    Явный старт мгновенной аренды (вызов из NEW_booking_entry).
    """
    await state.clear()
    await ensure_common_tables(db)
    await _ensure_instant_table(db)

    locs = await db.execute(
        """
        SELECT DISTINCT l.id, l.name
          FROM locations l
          JOIN boards b ON b.location_id = l.id
         WHERE COALESCE(b.is_active,1)=1
           AND COALESCE(l.is_active,1)=1
           AND COALESCE(b.quantity,0) > 0
         ORDER BY l.name
        """,
        fetchall=True
    )

    if not locs:
        await msg.answer("❌ Сейчас нет доступных локаций.", reply_markup=main_menu())
        return

    kb = InlineKeyboardBuilder()
    for lid, lname in locs:
        kb.button(text=lname, callback_data=f"loc_{lid}")
    kb.adjust(1)

    await msg.answer("Выберите локацию:", reply_markup=kb.as_markup())
    await state.set_state(InstantFlow.choosing_location)


def register_instant_booking(router: Router, db):
    """
    Регистрируем цепочку хендлеров для дальнейших шагов мгновенной аренды.
    Также на всякий случай ловим нажатие 'mode:instant' и делегируем в start_instant_booking.
    """

    # На случай, если кто-то всё ещё шлёт mode:instant
    @router.callback_query(StateFilter(NewBookingChoice.choosing_mode), F.data == "mode:instant")
    async def inst_start_compat(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        await start_instant_booking(cq.message, state, db)

    @router.callback_query(StateFilter(InstantFlow.choosing_location), F.data.startswith("loc_"))
    async def inst_choose_loc(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        loc_id = int(cq.data.split("_", 1)[1])
        await state.update_data(location_id=loc_id)

        boards = await db.execute(
            """
            SELECT id, name, price, COALESCE(quantity,0) AS avail
              FROM boards
             WHERE location_id = ?
               AND COALESCE(is_active,1)=1
               AND COALESCE(quantity,0) > 0
             ORDER BY name
            """,
            (loc_id,), fetchall=True
        )

        if not boards:
            return await cq.answer("❌ В этой локации нет доступных досок.", show_alert=True)

        kb = InlineKeyboardBuilder()
        for bid, name, price, avail in boards:
            kb.button(text=f"{name} — {int(price)}₽/ч (свободно {avail})", callback_data=f"inst_{bid}")
        kb.adjust(1)
        await cq.message.edit_text("Выберите доску:", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.select_board)

    @router.callback_query(StateFilter(InstantFlow.select_board), F.data.startswith("inst_"))
    async def inst_select_board(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split("_", 1)[1])

        row = await db.execute(
            "SELECT name, price, COALESCE(quantity,0) AS avail FROM boards WHERE id = ?",
            (bid,), fetch="one"
        )
        if not row:
            return await cq.message.answer("❌ Доска не найдена.")
        name, price, avail = row
        if avail < 1:
            return await cq.answer("❌ Нет свободных досок.", show_alert=True)

        await state.update_data(board_id=bid, board_name=name, price=price, avail=avail)

        # спрашиваем количество
        kb = InlineKeyboardBuilder()
        max_q = min(int(avail), 5)
        for q in range(1, max_q + 1):
            kb.button(text=str(q), callback_data=f"qty_{q}")
        kb.adjust(5)
        await cq.message.edit_text("Сколько досок вам нужно?", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.select_quantity)

    @router.callback_query(StateFilter(InstantFlow.select_quantity), F.data.startswith("qty_"))
    async def inst_select_quantity(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        qty = int(cq.data.split("_", 1)[1])
        await state.update_data(quantity=qty)

        # длительность
        options = [30, 60, 120, 180]
        kb = InlineKeyboardBuilder()
        for m in options:
            kb.button(text=(f"{m} мин" if m < 60 else f"{m//60} ч"), callback_data=f"dur_{m}")
        kb.adjust(4)
        await cq.message.edit_text("На сколько минут?", reply_markup=kb.as_markup())
        await state.set_state(InstantFlow.select_duration)

    @router.callback_query(StateFilter(InstantFlow.select_duration), F.data.startswith("dur_"))
    async def inst_select_duration(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        m = int(cq.data.split("_", 1)[1])
        data = await state.get_data()

        now = datetime.now()
        start_dt = (now + timedelta(minutes=5)).replace(second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=m)
        amount = float(data["price"]) * (m / 60.0) * int(data.get("quantity", 1))

        await state.update_data(
            date=start_dt.date().isoformat(),
            start_time=start_dt.hour,
            start_minute=start_dt.minute,
            duration=m,
            amount=amount
        )

        text = (
            "📝 Подтвердите бронь:\n\n"
            f"🛶 {data['board_name']} × {data['quantity']}\n"
            f"🕒 {start_dt:%H:%M}–{end_dt:%H:%M}\n"
            f"⏳ {m} мин\n"
            f"💰 {amount:.2f} ₽"
        )
        await cq.message.edit_text(text, reply_markup=confirm_booking_keyboard())
        await state.set_state(InstantFlow.confirm)

        # напоминание за 5 минут
        delay = (start_dt - now - timedelta(minutes=5)).total_seconds()
        if delay > 0:
            asyncio.create_task(_remind_start(cq.bot, cq.from_user.id, data["board_name"], delay))

    async def _remind_start(bot, user_id: int, board_name: str, delay: float):
        await asyncio.sleep(delay)
        try:
            await bot.send_message(user_id, f"⏰ Ваша мгновенная аренда {board_name} начнётся через 5 минут.")
        except Exception:
            pass

    @router.callback_query(StateFilter(InstantFlow.confirm), F.data == "confirm_booking")
    async def inst_confirm(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.set_state(BookingState.select_payment)
        await cq.message.edit_text("Выберите способ оплаты:", reply_markup=payment_choice_keyboard())

    # Ниже — «ручное» создание записи для cash/card.
    # Если используешь NEW_payments.py (инвойс/карта/нал) — обязательна регистрация его роутера!
    @router.callback_query(StateFilter(BookingState.select_payment), F.data == "pay_card")
    async def instant_pay_card(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()

        # Сохраняем бронь с локальным временем
        await db.execute(
            """
            INSERT INTO bookings (
              user_id, board_id, board_name,
              date, start_time, start_minute,
              duration, quantity, amount,
              status, payment_method, created_at
            ) VALUES (
              ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              'waiting_card', 'card',
              datetime('now','localtime')
            )
            """,
            (
                cq.from_user.id,
                data["board_id"],
                data["board_name"],
                data["date"],
                data["start_time"],
                data["start_minute"],
                data["duration"],
                data["quantity"],
                data["amount"],
            ),
            commit=True
        )
        # Уменьшаем доступное количество
        await db.execute(
            "UPDATE boards SET quantity = quantity - ? WHERE id = ?",
            (data["quantity"], data["board_id"]), commit=True
        )
        # Уведомляем партнёра
        try:
            await notify_partner(
                cq.bot, db, data["board_id"],
                f"🆕 Мгновенная бронь (карта): {data['board_name']} ×{data['quantity']} на {data['duration']} мин\n"
                f"Сумма: {data['amount']:.2f} ₽"
            )
        except Exception:
            # не валим поток, если чат партнёра не найден
            pass

        await cq.message.answer("✅ Бронь создана! Ожидайте подтверждения партнёра.", reply_markup=main_menu())
        await state.clear()

    @router.callback_query(StateFilter(BookingState.select_payment), F.data == "pay_cash")
    async def instant_pay_cash(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()

        await db.execute(
            """
            INSERT INTO bookings (
              user_id, board_id, board_name,
              date, start_time, start_minute,
              duration, quantity, amount,
              status, payment_method, created_at
            ) VALUES (
              ?, ?, ?,
              ?, ?, ?,
              ?, ?, ?,
              'waiting_cash', 'cash',
              datetime('now','localtime')
            )
            """,
            (
                cq.from_user.id,
                data["board_id"],
                data["board_name"],
                data["date"],
                data["start_time"],
                data["start_minute"],
                data["duration"],
                data["quantity"],
                data["amount"],
            ),
            commit=True
        )
        await db.execute(
            "UPDATE boards SET quantity = quantity - ? WHERE id = ?",
            (data["quantity"], data["board_id"]), commit=True
        )
        try:
            await notify_partner(
                cq.bot, db, data["board_id"],
                f"🆕 Мгновенная бронь (наличка): {data['board_name']} ×{data['quantity']} на {data['duration']} мин\n"
                f"Сумма: {data['amount']:.2f} ₽"
            )
        except Exception:
            pass

        await cq.message.answer("✅ Бронь создана! Ожидайте подтверждения партнёра.", reply_markup=main_menu())
        await state.clear()

    @router.callback_query(F.data == "cancel_booking")
    async def inst_cancel(cq: CallbackQuery, state: FSMContext):
        await cq.answer("❌ Бронь отменена.", show_alert=True)
        await cq.message.edit_text("Отменено.", reply_markup=main_menu())
        await state.clear()
