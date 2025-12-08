# keyboards/new_admin_menu.py
# -*- coding: utf-8 -*-

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ====== КОНСТАНТЫ ТЕКСТОВ КНОПОК ======
BTN_LOCATIONS           = "📍 Локации"
BTN_BOARDS              = "📄 Доски"
BTN_FINANCE             = "📈 Финансы"
BTN_USERS               = "👥 Пользователи"
BTN_BOOKINGS            = "📋 Все брони"
BTN_APPROVALS           = "✅ Одобрения партнёров"
BTN_WITHDRAWALS         = "💸 Заявки на вывод"   # ← новая кнопка
BTN_BACK                = "⬅️ Назад"

# Финансы
BTN_TURNOVER_TODAY      = "💵 Оборот сегодня"
BTN_TURNOVER_MONTH      = "📅 За месяц"
BTN_BY_METHOD           = "💳 По способам оплаты"
BTN_EXPENSES            = "📘 Расходы"
BTN_INCOME              = "📗 Доходы"

def new_admin_menu() -> ReplyKeyboardMarkup:
    """Главное меню админа"""
    keyboard = [
        [KeyboardButton(text=BTN_LOCATIONS),      KeyboardButton(text=BTN_BOARDS)],
        [KeyboardButton(text=BTN_FINANCE),        KeyboardButton(text=BTN_USERS)],
        [KeyboardButton(text=BTN_BOOKINGS),       KeyboardButton(text=BTN_APPROVALS)],
        [KeyboardButton(text=BTN_WITHDRAWALS)],  # кнопка для одобрения заявок на вывод
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def new_finance_menu() -> ReplyKeyboardMarkup:
    """Подменю раздела Финансы"""
    keyboard = [
        [KeyboardButton(text=BTN_TURNOVER_TODAY), KeyboardButton(text=BTN_TURNOVER_MONTH)],
        [KeyboardButton(text=BTN_BY_METHOD)],
        [KeyboardButton(text=BTN_EXPENSES),       KeyboardButton(text=BTN_INCOME)],
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def user_main_menu() -> ReplyKeyboardMarkup:
    """Меню обычного пользователя"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="🏄 Новая бронь")
    kb.button(text="🛍️ Каталог объявлений")
    kb.button(text="🌟 Отзывы")
    kb.button(text="👤 Мой кабинет")
    kb.button(text="ℹ️ Помощь")
    kb.button(text="📞 Контакты")
    kb.button(text="📄 Оферта")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)
