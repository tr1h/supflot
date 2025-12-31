"""Партнерские клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_partner_menu() -> InlineKeyboardMarkup:
    """Главное меню партнера"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Локации", callback_data="partner:locations")],
            [InlineKeyboardButton(text="🏄 Доски", callback_data="partner:boards")],
            [InlineKeyboardButton(text="📋 Бронирования", callback_data="partner:bookings")],
            [InlineKeyboardButton(text="⭐ Отзывы", callback_data="partner:reviews")],
            [InlineKeyboardButton(text="🌙 Суточная аренда", callback_data="partner:daily")],
            [InlineKeyboardButton(text="💰 Кошелек", callback_data="partner:wallet")],
                   [InlineKeyboardButton(text="👥 Сотрудники", callback_data="partner:employees")],
                   [InlineKeyboardButton(text="📖 Документация", callback_data="docs:menu")],
                   [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )
    return keyboard


def get_location_management_keyboard(location_id: int) -> InlineKeyboardMarkup:
    """Управление локацией"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"partner:location_edit:{location_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"partner:location_delete:{location_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:locations")],
        ]
    )
    return keyboard


def get_board_management_keyboard(board_id: int) -> InlineKeyboardMarkup:
    """Управление доской"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"partner:board_edit:{board_id}")],
            [InlineKeyboardButton(text="🖼️ Фото", callback_data=f"partner:board_images:{board_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"partner:board_delete:{board_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:boards")],
        ]
    )
    return keyboard


def get_booking_action_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Действия с бронированием"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"partner:booking_confirm:{booking_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"partner:booking_cancel:{booking_id}")],
            [InlineKeyboardButton(text="✅ Завершить", callback_data=f"partner:booking_complete:{booking_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:bookings")],
        ]
    )
    return keyboard


def get_board_edit_keyboard(board_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования доски"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"partner:board_edit_name:{board_id}")],
            [InlineKeyboardButton(text="💰 Цена", callback_data=f"partner:board_edit_price:{board_id}")],
            [InlineKeyboardButton(text="📝 Описание", callback_data=f"partner:board_edit_description:{board_id}")],
            [InlineKeyboardButton(text="🔢 Количество", callback_data=f"partner:board_edit_quantity:{board_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:board:{board_id}")],
        ]
    )
    return keyboard


def get_board_images_keyboard(board_id: int, images_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура для управления фото доски"""
    buttons = []
    if images_count > 0:
        buttons.append([InlineKeyboardButton(text="➕ Добавить фото", callback_data=f"partner:board_image_add:{board_id}")])
        buttons.append([InlineKeyboardButton(text="🗑️ Удалить фото", callback_data=f"partner:board_image_delete:{board_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ Добавить фото", callback_data=f"partner:board_image_add:{board_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:board:{board_id}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_reviews_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню отзывов партнера"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="partner:reviews_stats")],
            [InlineKeyboardButton(text="📋 Все отзывы", callback_data="partner:reviews_list")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:menu")],
        ]
    )
    return keyboard


def get_board_management_keyboard_with_reviews(board_id: int) -> InlineKeyboardMarkup:
    """Управление доской с кнопкой отзывов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"partner:board_edit:{board_id}")],
            [InlineKeyboardButton(text="🖼️ Фото", callback_data=f"partner:board_images:{board_id}")],
            [InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"partner:board_reviews:{board_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"partner:board_delete:{board_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:boards")],
        ]
    )
    return keyboard
