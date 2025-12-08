# keyboards/__init__.py
from .admin import admin_main_menu, admin_boards_menu, admin_finance_menu
from .partner import partner_main_menu, partner_board_confirm_kb, partner_ad_confirm_kb
from .new_finance_menu import new_finance_menu            # если отдельным файлом
from .new_partner_menu import partner_finance_menu
from .user import user_main_menu, booking_choice_keyboard, review_kb
from .common import (
    confirm_booking_keyboard,
    payment_choice_keyboard,
    card_paid_keyboard,
    cash_paid_keyboard,
    dates_keyboard,
    duration_keyboard,
    time_slots_keyboard,
    quantity_keyboard,
)

# новое админ-меню и константы
from .new_admin_menu import (
    new_admin_menu,
    BTN_LOCATIONS, BTN_BOARDS, BTN_FINANCE, BTN_USERS,
    BTN_BOOKINGS, BTN_APPROVALS, BTN_BACK,
    BTN_TURNOVER_TODAY, BTN_TURNOVER_MONTH, BTN_BY_METHOD,
    BTN_EXPENSES, BTN_INCOME,
)

# Псевдонимы
new_main_menu = user_main_menu
main_menu = user_main_menu

__all__ = [
    # старые
    "admin_main_menu", "admin_boards_menu", "admin_finance_menu",
    "partner_main_menu", "partner_board_confirm_kb", "partner_ad_confirm_kb",
    "user_main_menu", "booking_choice_keyboard", "review_kb",
    "confirm_booking_keyboard", "payment_choice_keyboard",
    "card_paid_keyboard", "cash_paid_keyboard",
    "dates_keyboard", "duration_keyboard", "time_slots_keyboard", "quantity_keyboard",
    "new_finance_menu", "new_partner_menu",
    "new_main_menu", "main_menu",
    # новые
    "new_admin_menu",
    "BTN_LOCATIONS", "BTN_BOARDS", "BTN_FINANCE", "BTN_USERS",
    "BTN_BOOKINGS", "BTN_APPROVALS", "BTN_BACK",
    "BTN_TURNOVER_TODAY", "BTN_TURNOVER_MONTH", "BTN_BY_METHOD",
    "BTN_EXPENSES", "BTN_INCOME",
]
