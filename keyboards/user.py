"""Пользовательские клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Новая бронь")],
            [KeyboardButton(text="📋 Мои брони"), KeyboardButton(text="📚 Каталог")],
            [KeyboardButton(text="⭐ Отзывы"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="💬 Контакты"), KeyboardButton(text="📖 Документация")],
            [KeyboardButton(text="📄 Оферта")],
        ],
        resize_keyboard=True
    )
    return keyboard


def get_booking_type_keyboard() -> InlineKeyboardMarkup:
    """Типы бронирования"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Обычная бронь", callback_data="booking_type:regular")],
            [InlineKeyboardButton(text="⚡ Мгновенная бронь", callback_data="booking_type:instant")],
            [InlineKeyboardButton(text="🌙 Суточная аренда", callback_data="booking_type:daily")],
            [InlineKeyboardButton(text="📦 Мультибронь", callback_data="booking_type:multi")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
        ]
    )
    return keyboard


def get_back_keyboard(callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
        ]
    )
    return keyboard


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Способы оплаты"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Telegram Pay", callback_data="payment:telegram")],
            [InlineKeyboardButton(text="💳 Банковская карта", callback_data="payment:card")],
            [InlineKeyboardButton(text="💵 Перевод на карту", callback_data="payment:card_transfer")],
            [InlineKeyboardButton(text="💵 Наличные", callback_data="payment:cash")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_booking")],
        ]
    )
    return keyboard


def get_locations_keyboard(locations: list) -> InlineKeyboardMarkup:
    """Клавиатура с локациями"""
    buttons = []
    for loc in locations:
        buttons.append([InlineKeyboardButton(
            text=f"📍 {loc['name']}",
            callback_data=f"location:{loc['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_booking")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_boards_keyboard(boards: list) -> InlineKeyboardMarkup:
    """Клавиатура с досками"""
    buttons = []
    for board in boards:
        status = "✅" if board['is_active'] and board['quantity'] > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {board['name']} - {board['price']:.0f}₽/ч",
            callback_data=f"board:{board['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_locations")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_date_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора даты (ближайшие 14 дней)"""
    from datetime import date, timedelta
    
    buttons = []
    today = date.today()
    
    # Создаем кнопки на 14 дней вперед
    for i in range(14):
        booking_date = today + timedelta(days=i)
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][booking_date.weekday()]
        
        # Форматируем дату для отображения
        date_text = f"{day_name} {booking_date.day:02d}.{booking_date.month:02d}.{booking_date.year}"
        
        # Если сегодня, добавляем "Сегодня"
        if i == 0:
            date_text = f"Сегодня ({booking_date.day:02d}.{booking_date.month:02d})"
        elif i == 1:
            date_text = f"Завтра ({booking_date.day:02d}.{booking_date.month:02d})"
        
        buttons.append([InlineKeyboardButton(
            text=date_text,
            callback_data=f"date:{booking_date.strftime('%Y-%m-%d')}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boards")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени"""
    buttons = []
    # Время с 8:00 до 22:00 с интервалом в 1 час
    for hour in range(8, 23):
        buttons.append([InlineKeyboardButton(
            text=f"{hour}:00",
            callback_data=f"time:{hour}:0"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_date")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_duration_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора длительности"""
    durations = [
        (30, "30 мин"),
        (60, "1 час"),
        (90, "1.5 часа"),
        (120, "2 часа"),
        (180, "3 часа"),
        (240, "4 часа"),
    ]
    buttons = []
    for duration_minutes, duration_text in durations:
        buttons.append([InlineKeyboardButton(
            text=duration_text,
            callback_data=f"duration:{duration_minutes}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quantity_keyboard(max_quantity: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура для выбора количества досок"""
    buttons = []
    for qty in range(1, min(max_quantity + 1, 11)):
        buttons.append([InlineKeyboardButton(
            text=f"{qty} шт.",
            callback_data=f"quantity:{qty}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_duration")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

