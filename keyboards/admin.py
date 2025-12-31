"""Админские клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админа"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Партнеры", callback_data="admin:partners")],
            [InlineKeyboardButton(text="📍 Локации", callback_data="admin:locations")],
            [InlineKeyboardButton(text="🏄 Доски", callback_data="admin:boards")],
            [InlineKeyboardButton(text="📋 Бронирования", callback_data="admin:bookings")],
            [InlineKeyboardButton(text="💰 Финансы", callback_data="admin:finance")],
            [InlineKeyboardButton(text="⭐ Отзывы", callback_data="admin:reviews")],
            [InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="📢 Уведомления", callback_data="admin:notifications")],
            [InlineKeyboardButton(text="📖 Документация", callback_data="docs:menu")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )
    return keyboard


def get_partner_action_keyboard(partner_id: int) -> InlineKeyboardMarkup:
    """Действия с партнером"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin:partner_approve:{partner_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:partner_reject:{partner_id}")],
            [InlineKeyboardButton(text="🔒 Заблокировать/Разблокировать", callback_data=f"admin:partner_block:{partner_id}")],
            [InlineKeyboardButton(text="💰 Комиссия", callback_data=f"admin:partner_commission:{partner_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:partners")],
        ]
    )
    return keyboard


def get_withdraw_action_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Действия с запросом на вывод"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin:withdraw_approve:{request_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:withdraw_reject:{request_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:finance")],
        ]
    )
    return keyboard

