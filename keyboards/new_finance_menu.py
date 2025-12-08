# keyboards/new_finance_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def new_finance_menu():
    kb = [
        [KeyboardButton(text="📈 Доходы"), KeyboardButton(text="📉 Расходы")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
