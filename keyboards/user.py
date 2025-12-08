# keyboards/user.py
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import os

# URL для Mini App (локально или на хостинге)
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://supflot-website.onrender.com/miniapp/")

def user_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    # Кнопка Web App для Mini App
    kb.button(
        text="🚀 Открыть приложение",
        web_app=WebAppInfo(url=MINIAPP_URL)
    )
    kb.button(text="🏄 Новая бронь")
    kb.button(text="🛍️ Каталог объявлений")
    kb.button(text="🌟 Отзывы")
    kb.button(text="👤 Мой кабинет")
    kb.button(text="ℹ️ Помощь")
    kb.button(text="📞 Контакты")
    kb.button(text="📄 Оферта")
    kb.adjust(1, 2, 2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def booking_choice_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 У воды (моментально)", callback_data="mode:instant")
    kb.button(text="📝 Предварительная", callback_data="mode:regular")
    kb.button(text="📆 Суточная аренда", callback_data="mode:daily")
    kb.button(text="❌ Отмена", callback_data="mode:cancel")
    kb.adjust(1)
    return kb.as_markup()


def review_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Написать отзыв", callback_data="write_review")
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()
