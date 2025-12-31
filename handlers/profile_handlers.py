"""Обработчики профиля пользователя"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from keyboards.user import get_back_keyboard

logger = logging.getLogger(__name__)


class ProfileStates(StatesGroup):
    """Состояния для редактирования профиля"""
    editing_name = State()


def get_profile_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню профиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать имя", callback_data="profile:edit_name")],
        [InlineKeyboardButton(text="📋 История бронирований", callback_data="profile:booking_history")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="profile:stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")],
    ])


def register_profile_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков профиля"""
    
    @router.message(F.text == "👤 Профиль")
    async def profile_menu(message: Message):
        """Меню профиля"""
        user_id = message.from_user.id
        
        user = await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Получаем статистику
        bookings_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ?",
            (user_id,)
        )
        total_spent = await db.fetchone(
            """SELECT SUM(amount) as total FROM bookings 
               WHERE user_id = ? AND status IN ('active', 'completed', 'waiting_card', 'waiting_cash')""",
            (user_id,)
        )
        completed_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )
        
        text = "👤 <b>Мой профиль</b>\n\n"
        text += f"Имя: {user.get('full_name', 'Не указано')}\n"
        if user.get('username'):
            text += f"Username: @{user['username']}\n"
        text += f"ID: {user_id}\n"
        if user.get('reg_date'):
            text += f"Дата регистрации: {user['reg_date'][:10] if len(user['reg_date']) > 10 else user['reg_date']}\n"
        
        text += "\n📊 <b>Статистика:</b>\n"
        text += f"Всего бронирований: {bookings_count['count'] if bookings_count else 0}\n"
        text += f"Завершено: {completed_count['count'] if completed_count else 0}\n"
        if total_spent and total_spent['total']:
            text += f"Потрачено: {total_spent['total']:.2f}₽\n"
        
        text += "\nВыберите действие:"
        
        await message.answer(text, reply_markup=get_profile_menu_keyboard())
    
    @router.callback_query(F.data == "profile:edit_name")
    async def profile_edit_name_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования имени"""
        await callback.answer()
        await state.set_state(ProfileStates.editing_name)
        
        text = "✏️ <b>Редактирование имени</b>\n\n"
        text += "Введите новое имя:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("profile:menu"))
        except:
            await callback.message.answer(text, reply_markup=get_back_keyboard("profile:menu"))
    
    @router.message(ProfileStates.editing_name, F.text)
    async def profile_edit_name_save(message: Message, state: FSMContext):
        """Сохранение нового имени"""
        new_name = message.text.strip()
        
        if len(new_name) < 2:
            await message.answer("❌ Имя слишком короткое. Минимум 2 символа.")
            return
        
        if len(new_name) > 100:
            await message.answer("❌ Имя слишком длинное. Максимум 100 символов.")
            return
        
        user_id = message.from_user.id
        
        try:
            await db.execute(
                "UPDATE users SET full_name = ? WHERE id = ?",
                (new_name, user_id)
            )
            
            text = f"✅ Имя успешно обновлено!\n\n"
            text += f"Новое имя: {new_name}"
            
            await message.answer(text, reply_markup=get_back_keyboard("profile:menu"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating user name: {e}")
            await message.answer("❌ Ошибка при обновлении имени. Попробуйте еще раз.")
    
    @router.callback_query(F.data == "profile:booking_history")
    async def profile_booking_history(callback: CallbackQuery):
        """История бронирований"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Получаем все бронирования (последние 50)
        bookings = await db.fetchall(
            """SELECT * FROM bookings 
               WHERE user_id = ? 
               ORDER BY created_at DESC
               LIMIT 50""",
            (user_id,)
        )
        
        if not bookings:
            text = "📋 <b>История бронирований</b>\n\n"
            text += "У вас пока нет бронирований."
            keyboard = get_back_keyboard("profile:menu")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
            return
        
        from handlers.user_bookings_handlers import format_booking_status
        
        text = f"📋 <b>История бронирований ({len(bookings)})</b>\n\n"
        
        # Группируем по статусам
        status_groups = {}
        for booking in bookings:
            status = booking['status']
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(booking)
        
        # Показываем последние 10
        for booking in bookings[:10]:
            text += f"#{booking['id']} - {booking['board_name']}\n"
            text += f"📅 {booking['date']} в {booking['start_time']}:{booking['start_minute']:02d}\n"
            text += f"💰 {booking['amount']:.2f}₽ - {format_booking_status(booking['status'])}\n\n"
        
        if len(bookings) > 10:
            text += f"... и еще {len(bookings) - 10} бронирований"
        
        keyboard = get_back_keyboard("profile:menu")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "profile:stats")
    async def profile_stats(callback: CallbackQuery):
        """Статистика пользователя"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Получаем статистику
        total_bookings = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ?",
            (user_id,)
        )
        
        completed_bookings = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )
        
        active_bookings = await db.fetchone(
            """SELECT COUNT(*) as count FROM bookings 
               WHERE user_id = ? AND status IN ('active', 'waiting_partner', 'waiting_card', 'waiting_cash')""",
            (user_id,)
        )
        
        total_spent = await db.fetchone(
            """SELECT SUM(amount) as total FROM bookings 
               WHERE user_id = ? AND status IN ('active', 'completed', 'waiting_card', 'waiting_cash')""",
            (user_id,)
        )
        
        # Средний чек
        avg_amount = await db.fetchone(
            """SELECT AVG(amount) as avg FROM bookings 
               WHERE user_id = ? AND status IN ('active', 'completed', 'waiting_card', 'waiting_cash')""",
            (user_id,)
        )
        
        text = "📊 <b>Статистика</b>\n\n"
        text += f"Всего бронирований: {total_bookings['count'] if total_bookings else 0}\n"
        text += f"Активных: {active_bookings['count'] if active_bookings else 0}\n"
        text += f"Завершено: {completed_bookings['count'] if completed_bookings else 0}\n\n"
        
        if total_spent and total_spent['total']:
            text += f"💰 Потрачено всего: {total_spent['total']:.2f}₽\n"
        if avg_amount and avg_amount['avg']:
            text += f"📈 Средний чек: {avg_amount['avg']:.2f}₽\n"
        
        keyboard = get_back_keyboard("profile:menu")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "profile:menu")
    async def profile_menu_callback(callback: CallbackQuery):
        """Меню профиля (из callback)"""
        await callback.answer()
        user_id = callback.from_user.id
        
        user = await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден.")
            return
        
        # Получаем статистику
        bookings_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ?",
            (user_id,)
        )
        total_spent = await db.fetchone(
            """SELECT SUM(amount) as total FROM bookings 
               WHERE user_id = ? AND status IN ('active', 'completed', 'waiting_card', 'waiting_cash')""",
            (user_id,)
        )
        completed_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE user_id = ? AND status = 'completed'",
            (user_id,)
        )
        
        text = "👤 <b>Мой профиль</b>\n\n"
        text += f"Имя: {user.get('full_name', 'Не указано')}\n"
        if user.get('username'):
            text += f"Username: @{user['username']}\n"
        text += f"ID: {user_id}\n"
        if user.get('reg_date'):
            text += f"Дата регистрации: {user['reg_date'][:10] if len(user['reg_date']) > 10 else user['reg_date']}\n"
        
        text += "\n📊 <b>Статистика:</b>\n"
        text += f"Всего бронирований: {bookings_count['count'] if bookings_count else 0}\n"
        text += f"Завершено: {completed_count['count'] if completed_count else 0}\n"
        if total_spent and total_spent['total']:
            text += f"Потрачено: {total_spent['total']:.2f}₽\n"
        
        text += "\nВыберите действие:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_profile_menu_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_profile_menu_keyboard())

