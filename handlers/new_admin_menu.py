# keyboards/new_admin_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def new_admin_menu():
    kb = [
        [KeyboardButton(text="📍 Локации"), KeyboardButton(text="📄 Доски")],
        [KeyboardButton(text="📊 Финансы"), KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
