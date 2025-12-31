# -*- coding: utf-8 -*-
"""
FSM-состояния для пользовательского бронирования SUP.

Используются тремя сценариями:
1) Предварительная бронь (по дате/времени)
2) Мгновенная аренда "у воды"
3) Суточная аренда (категория "как авто") — запускает другой роутер, но можем хранить контекст.

Также добавлено отдельное состояние выбора режима (NewBookingChoice),
чтобы не перегружать BookingState.
"""

from aiogram.fsm.state import State, StatesGroup


class NewBookingChoice(StatesGroup):
    choosing_mode = State()


class BookingState(StatesGroup):
    select_location   = State()
    select_board      = State()
    select_date       = State()
    select_duration   = State()
    select_time       = State()
    select_quantity   = State()
    confirm_amount    = State()
    enter_name        = State()
    enter_phone       = State()
    select_payment    = State()
    wait_card_paid    = State()
    wait_cash_paid    = State()
    cancel            = State()


class InstantState(StatesGroup):
    select_board    = State()
    select_duration = State()


class DailyState(StatesGroup):
    select_location = State()
    select_board    = State()
    select_date     = State()
    select_duration = State()
    confirm         = State()

# --- Состояния для админ-добавления пользователя ---
class AdminUserState(StatesGroup):
    waiting_user_id   = State()
    waiting_username  = State()
    waiting_full_name = State()
    waiting_phone     = State()