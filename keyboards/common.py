# keyboards/common.py
# -*- coding: utf-8 -*-
"""
Универсальные inline‑клавиатуры для сценариев бронирования:
– главное меню (main_menu)
– подтверждение, оплата, выбор даты, времени, количества и т.п.
"""

from datetime import datetime, timedelta

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .user import user_main_menu as main_menu

from config import WORK_HOURS
from handlers.NEW_utils import WEEKDAYS_RU

# Алиас главного меню пользователя



# ✅ Подтверждение брони
def confirm_booking_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отменить",    callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()


# 💳 Выбор способа оплаты
def payment_choice_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💠 Telegram Pay", callback_data="pay_telegram")
    builder.button(text="💳 На карту",      callback_data="pay_card")
    builder.button(text="💵 Наличными",     callback_data="pay_cash")
    builder.button(text="❌ Отмена",        callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()


# ✅ Я оплатил (для карты)
def card_paid_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я оплатил", callback_data="card_paid")
    builder.button(text="❌ Отменить",  callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


# ✅ Оплачено (наличными)
def cash_paid_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оплачено", callback_data="cash_paid")
    builder.button(text="❌ Отменить", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


# 📅 Календарь на неделю
async def dates_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.now().date()
    now_h = datetime.now().hour

    for i in range(7):
        d = today + timedelta(days=i)
        # если сегодня — и время уже за рабочим днем, пропускаем
        if i == 0 and now_h >= WORK_HOURS[1]:
            continue
        label = f"{WEEKDAYS_RU[d.weekday()]} {d.day:02}.{d.month:02}"
        builder.button(text=label, callback_data=f"date_{d.isoformat()}")
    builder.adjust(4)
    return builder.as_markup()


# ⏱️ Длительность аренды (часы)
async def duration_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start_hour, end_hour = WORK_HOURS
    for h in range(1, end_hour - start_hour + 1):
        builder.button(text=f"{h} ч", callback_data=f"dur_h_{h}")
    builder.adjust(3)
    return builder.as_markup()


# ⏰ Слоты по времени с учётом занятости
async def time_slots_keyboard(
    db,
    date: str,
    board_id: int,
    duration: int
) -> types.InlineKeyboardMarkup:
    start, end = WORK_HOURS
    # получаем всего доступных досок
    row = await db.execute("SELECT total FROM boards WHERE id=?", (board_id,), fetch="one")
    total = row[0] if row else 0

    # занятость по часам
    occ = await db.execute(
        "SELECT start_time, duration, quantity FROM bookings "
        "WHERE board_id=? AND date=? AND status IN ('active','waiting_card','waiting_cash')",
        (board_id, date),
        fetchall=True
    )
    occ_map = {h: 0 for h in range(start, end)}
    for s, dur, qty in occ:
        for hh in range(s, s + dur):
            if hh in occ_map:
                occ_map[hh] += qty

    now_h = datetime.now().hour
    is_today = (date == datetime.now().date().isoformat())

    builder = InlineKeyboardBuilder()
    for h in range(start, end - duration + 1):
        free = total - max(occ_map.get(x, 0) for x in range(h, h + duration))
        label = f"{h:02}:00–{h + duration:02}:00"

        if is_today and h <= now_h:
            builder.button(text=f"🔴 {label}", callback_data="ignore")
        elif free <= 0:
            builder.button(text=f"🔴 {label} (Нет)", callback_data="ignore")
        else:
            emoji = "🟢" if free == total else "🟡"
            builder.button(text=f"{emoji} {label} ({free})", callback_data=f"time_{h}")
    builder.button(text="◀️ Назад", callback_data="back_to_start")
    builder.adjust(2)
    return builder.as_markup()


# 🔢 Количество досок
async def quantity_keyboard(
    db,
    board_id: int,
    date: str,
    start_h: int,
    duration: int
) -> types.InlineKeyboardMarkup:
    # всего досок
    row = await db.execute("SELECT total FROM boards WHERE id=?", (board_id,), fetch="one")
    total = row[0] if row else 0

    # занятость в выбранный интервал
    occ = await db.execute(
        "SELECT start_time, duration, quantity FROM bookings "
        "WHERE board_id=? AND date=? AND status IN ('active','waiting_card','waiting_cash')",
        (board_id, date),
        fetchall=True
    )
    busy = 0
    for s, dur, qty in occ:
        rng = range(s, s + dur)
        if any(h in rng for h in range(start_h, start_h + duration)):
            busy += qty

    free = max(0, total - busy)

    builder = InlineKeyboardBuilder()
    for q in range(1, free + 1):
        builder.button(text=str(q), callback_data=f"qty_{q}")
    builder.adjust(4)
    return builder.as_markup()


__all__ = [
    "main_menu",
    "confirm_booking_keyboard",
    "payment_choice_keyboard",
    "card_paid_keyboard",
    "cash_paid_keyboard",
    "dates_keyboard",
    "duration_keyboard",
    "time_slots_keyboard",
    "quantity_keyboard",
]
