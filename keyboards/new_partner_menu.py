from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def partner_finance_menu():
    kb = [
        [KeyboardButton(text="📗 Доходы"), KeyboardButton(text="📘 Расходы")],
        [KeyboardButton(text="💸 Запросить выплату")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
