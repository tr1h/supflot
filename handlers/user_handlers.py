# handlers/user_handlers.py

from aiogram.fsm.state import State, StatesGroup
from keyboards.user import user_main_menu


class BookingState(StatesGroup):
    select_payment = State()
    wait_card_paid = State()
    wait_cash_paid = State()
    # Добавь другие состояния, если нужно


def main_menu():
    return user_main_menu()
