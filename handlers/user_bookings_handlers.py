"""Обработчики для просмотра бронирований пользователем"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from core.database import Database
from keyboards.user import get_back_keyboard

logger = logging.getLogger(__name__)


def format_booking_status(status: str) -> str:
    """Форматирование статуса бронирования"""
    status_map = {
        "waiting_partner": "⏳ Ожидает подтверждения партнера",
        "active": "✅ Активно",
        "completed": "✔️ Завершено",
        "canceled": "❌ Отменено",
        "waiting_card": "💳 Ожидает оплаты (перевод)",
        "waiting_cash": "💵 Ожидает оплаты (наличные)",
        "waiting_daily": "⏳ Ожидает подтверждения",
    }
    return status_map.get(status, status)


def format_booking_text(booking: dict) -> str:
    """Форматирование текста бронирования"""
    text = f"📋 <b>Бронирование #{booking['id']}</b>\n\n"
    text += f"Доска: {booking['board_name']}\n"
    text += f"Дата: {booking['date']}\n"
    text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
    text += f"Длительность: {booking['duration']} мин\n"
    text += f"Количество: {booking['quantity']} шт.\n"
    text += f"Сумма: {booking['amount']:.2f}₽\n"
    text += f"Статус: {format_booking_status(booking['status'])}\n"
    
    if booking.get('payment_method'):
        payment_methods = {
            "telegram": "💳 Telegram Pay",
            "card": "💳 Банковская карта",
            "card_transfer": "💵 Перевод на карту",
            "cash": "💵 Наличные",
        }
        text += f"Оплата: {payment_methods.get(booking['payment_method'], booking['payment_method'])}\n"
    
    return text


def register_user_bookings_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков бронирований пользователя"""
    
    @router.message(F.text == "📋 Мои брони")
    async def my_bookings(message: Message, state: FSMContext):
        """Просмотр бронирований пользователя"""
        await state.clear()
        user_id = message.from_user.id
        
        # Получаем активные и недавние бронирования
        bookings = await db.fetchall(
            """SELECT * FROM bookings 
               WHERE user_id = ? 
               AND status IN ('waiting_partner', 'active', 'waiting_card', 'waiting_cash')
               ORDER BY date DESC, start_time DESC
               LIMIT 20""",
            (user_id,)
        )
        
        if not bookings:
            text = "📋 <b>Мои брони</b>\n\n"
            text += "У вас пока нет активных бронирований."
            await message.answer(text, reply_markup=get_back_keyboard())
            return
        
        text = f"📋 <b>Мои брони ({len(bookings)})</b>\n\n"
        text += "Активные бронирования:\n\n"
        
        for booking in bookings[:5]:  # Показываем первые 5
            text += f"#{booking['id']} - {booking['board_name']}\n"
            text += f"📅 {booking['date']} в {booking['start_time']}:{booking['start_minute']:02d}\n"
            text += f"{format_booking_status(booking['status'])}\n\n"
        
        if len(bookings) > 5:
            text += f"... и еще {len(bookings) - 5} бронирований"
        
        # Создаем клавиатуру с кнопками для просмотра деталей
        buttons = []
        for booking in bookings[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"#{booking['id']} - {booking['board_name']}",
                callback_data=f"booking_detail:{booking['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("booking_detail:"))
    async def booking_detail(callback: CallbackQuery):
        """Детали бронирования"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[1])
        
        booking = await db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
        
        if not booking:
            await callback.message.edit_text("❌ Бронирование не найдено.")
            return
        
        text = format_booking_text(booking)
        
        buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_bookings")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "back_to_bookings")
    async def back_to_bookings(callback: CallbackQuery, state: FSMContext):
        """Возврат к списку бронирований"""
        await callback.answer()
        user_id = callback.from_user.id
        
        bookings = await db.fetchall(
            """SELECT * FROM bookings 
               WHERE user_id = ? 
               AND status IN ('waiting_partner', 'active', 'waiting_card', 'waiting_cash')
               ORDER BY date DESC, start_time DESC
               LIMIT 20""",
            (user_id,)
        )
        
        if not bookings:
            await callback.message.edit_text(
                "У вас пока нет активных бронирований.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
            return
        
        text = f"📋 <b>Мои брони ({len(bookings)})</b>\n\n"
        text += "Активные бронирования:\n\n"
        
        for booking in bookings[:5]:
            text += f"#{booking['id']} - {booking['board_name']}\n"
            text += f"📅 {booking['date']} в {booking['start_time']}:{booking['start_minute']:02d}\n"
            text += f"{format_booking_status(booking['status'])}\n\n"
        
        buttons = []
        for booking in bookings[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"#{booking['id']} - {booking['board_name']}",
                callback_data=f"booking_detail:{booking['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)

