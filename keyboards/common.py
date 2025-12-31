"""Общие клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_confirm_keyboard(confirm_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=confirm_data),
                InlineKeyboardButton(text="❌ Нет", callback_data=cancel_data)
            ]
        ]
    )
    return keyboard



