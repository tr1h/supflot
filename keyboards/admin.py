# keyboards/admin.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def admin_main_menu():
    """
    Главное меню администратора.
    """
    kb = ReplyKeyboardBuilder()
    kb.button(text="📈 Финансы")
    kb.button(text="📋 Все брони")
    kb.button(text="🔧 Управление досками")
    kb.button(text="📍 Локации")
    kb.button(text="👥 Пользователи")
    kb.button(text="👥 Одобрение партнёров")
    kb.button(text="💳 Платежи")
    kb.button(text="📤 Рассылка")
    kb.button(text="⬅️ В меню пользователя")
    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)

def admin_boards_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📄 Список досок")
    kb.button(text="➕ Добавить доску")
    kb.button(text="⬅️ Назад")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)

def admin_finance_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="💵 Оборот сегодня")
    kb.button(text="📅 За месяц")
    kb.button(text="💳 По способу оплаты")
    kb.button(text="📍 По локациям")
    kb.button(text="🏄 По доскам")
    kb.button(text="➕ Добавить расход")
    kb.button(text="⬅️ Назад")
    kb.adjust(2, 2, 2)
    return kb.as_markup(resize_keyboard=True)
