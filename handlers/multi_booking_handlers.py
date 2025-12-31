"""Обработчики мультиброни (бронирование нескольких досок одновременно)"""
import logging
from datetime import date, datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from services.booking_service import BookingService
from keyboards.user import get_back_keyboard, get_date_keyboard, get_time_keyboard, get_quantity_keyboard
from utils.date_parser import parse_date, is_date_valid
from config import Config

logger = logging.getLogger(__name__)


class MultiBookingStates(StatesGroup):
    """Состояния для мультиброни"""
    choosing_location = State()
    choosing_boards = State()
    choosing_date = State()
    choosing_time = State()
    choosing_duration = State()
    choosing_quantities = State()
    confirming = State()
    choosing_payment = State()


def register_multi_booking_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков мультиброни"""
    booking_service = BookingService(db)
    
    @router.callback_query(F.data == "booking_type:multi")
    async def booking_type_multi(callback: CallbackQuery, state: FSMContext):
        """Мультибронь - несколько досок одновременно"""
        await callback.answer()
        await state.set_state(MultiBookingStates.choosing_location)
        await state.update_data(booking_type="multi", selected_boards=[])
        
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        if not locations:
            await callback.message.edit_text(
                "❌ К сожалению, сейчас нет доступных локаций.\nПопробуйте позже.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
            return
        
        from keyboards.user import get_locations_keyboard
        text = "🎯 <b>Мультибронь</b>\n\n"
        text += "Выберите несколько досок для одновременного бронирования.\n\n"
        text += "📍 <b>Выберите локацию:</b>"
        await callback.message.edit_text(text, reply_markup=get_locations_keyboard(locations))
    
    @router.callback_query(F.data.startswith("multi:location:"), MultiBookingStates.choosing_location)
    async def multi_location_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор локации для мультиброни"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        await state.update_data(location_id=location_id)
        await state.set_state(MultiBookingStates.choosing_boards)
        
        boards = await db.fetchall(
            """SELECT * FROM boards 
               WHERE location_id = ? AND is_active = 1 
               ORDER BY name""",
            (location_id,)
        )
        
        if not boards:
            await callback.message.edit_text(
                "❌ В этой локации нет доступных досок.",
                reply_markup=get_back_keyboard("booking_type:multi")
            )
            return
        
        location = await db.fetchone("SELECT name FROM locations WHERE id = ?", (location_id,))
        text = f"🎯 <b>Мультибронь</b>\n\n"
        text += f"📍 Локация: {location['name']}\n\n"
        text += "Выберите доски (можно выбрать несколько):"
        
        # Создаем клавиатуру с чекбоксами для каждой доски
        buttons = []
        data_state = await state.get_data()
        selected_board_ids = data_state.get("selected_board_ids", [])
        
        for board in boards[:20]:
            is_selected = board['id'] in selected_board_ids
            prefix = "✅" if is_selected else "⬜"
            buttons.append([InlineKeyboardButton(
                text=f"{prefix} {board['name']} - {board['price']:.0f}₽/ч",
                callback_data=f"multi:board_toggle:{board['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="➡️ Далее", callback_data="multi:next")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="booking_type:multi")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        if selected_board_ids:
            text += f"\n\nВыбрано досок: {len(selected_board_ids)}"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("multi:board_toggle:"), MultiBookingStates.choosing_boards)
    async def multi_board_toggle(callback: CallbackQuery, state: FSMContext):
        """Переключение выбора доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        data = await state.get_data()
        selected_board_ids = data.get("selected_board_ids", [])
        
        if board_id in selected_board_ids:
            selected_board_ids.remove(board_id)
        else:
            if len(selected_board_ids) >= 5:  # Ограничение на количество досок
                await callback.answer("❌ Можно выбрать максимум 5 досок одновременно", show_alert=True)
                return
            selected_board_ids.append(board_id)
        
        await state.update_data(selected_board_ids=selected_board_ids)
        
        # Обновляем клавиатуру
        location_id = data.get("location_id")
        boards = await db.fetchall(
            """SELECT * FROM boards 
               WHERE location_id = ? AND is_active = 1 
               ORDER BY name""",
            (location_id,)
        )
        
        location = await db.fetchone("SELECT name FROM locations WHERE id = ?", (location_id,))
        text = f"🎯 <b>Мультибронь</b>\n\n"
        text += f"📍 Локация: {location['name']}\n\n"
        text += "Выберите доски (можно выбрать несколько):"
        
        buttons = []
        for board in boards[:20]:
            is_selected = board['id'] in selected_board_ids
            prefix = "✅" if is_selected else "⬜"
            buttons.append([InlineKeyboardButton(
                text=f"{prefix} {board['name']} - {board['price']:.0f}₽/ч",
                callback_data=f"multi:board_toggle:{board['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="➡️ Далее", callback_data="multi:next")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="booking_type:multi")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        if selected_board_ids:
            text += f"\n\nВыбрано досок: {len(selected_board_ids)}"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "multi:next", MultiBookingStates.choosing_boards)
    async def multi_next_to_date(callback: CallbackQuery, state: FSMContext):
        """Переход к выбору даты"""
        await callback.answer()
        data = await state.get_data()
        selected_board_ids = data.get("selected_board_ids", [])
        
        if not selected_board_ids:
            await callback.answer("❌ Выберите хотя бы одну доску", show_alert=True)
            return
        
        await state.set_state(MultiBookingStates.choosing_date)
        
        text = f"🎯 <b>Мультибронь</b>\n\n"
        text += f"Выбрано досок: {len(selected_board_ids)}\n\n"
        text += "Выберите дату бронирования (для всех досок одинаковую):"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_date_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_date_keyboard())
    
    @router.callback_query(F.data.startswith("date:"), MultiBookingStates.choosing_date)
    async def multi_date_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор даты для мультиброни"""
        await callback.answer()
        try:
            date_str = callback.data.split(":")[1]
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            today = date.today()
            if booking_date < today:
                await callback.message.edit_text(
                    "❌ Нельзя выбрать дату в прошлом. Выберите другую дату.",
                    reply_markup=get_date_keyboard()
                )
                return
            
            await state.update_data(booking_date=booking_date.strftime("%Y-%m-%d"))
            await state.set_state(MultiBookingStates.choosing_time)
            
            text = f"🎯 <b>Мультибронь</b>\n\n"
            text += f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n\n"
            text += "⏰ Выберите время начала (для всех досок одинаковое):"
            
            await callback.message.edit_text(text, reply_markup=get_time_keyboard())
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing date: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при выборе даты. Попробуйте еще раз.",
                reply_markup=get_date_keyboard()
            )
    
    @router.callback_query(F.data.startswith("time:"), MultiBookingStates.choosing_time)
    async def multi_time_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор времени для мультиброни"""
        await callback.answer()
        try:
            parts = callback.data.split(":")
            hour = int(parts[1])
            minute = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing time: {e}")
            await callback.message.edit_text("❌ Ошибка при выборе времени.")
            return
        
        if hour < Config.WORK_HOURS_START or hour >= Config.WORK_HOURS_END:
            await callback.message.edit_text(
                f"❌ Время работы: {Config.WORK_HOURS_START}:00 - {Config.WORK_HOURS_END}:00",
                reply_markup=get_time_keyboard()
            )
            return
        
        await state.update_data(start_time=hour, start_minute=minute)
        await state.set_state(MultiBookingStates.choosing_duration)
        
        text = f"🎯 <b>Мультибронь</b>\n\n"
        text += f"⏰ Время начала: {hour}:{minute:02d}\n\n"
        text += "⏱ Выберите длительность (для всех досок одинаковую):"
        
        from keyboards.user import get_duration_keyboard
        await callback.message.edit_text(text, reply_markup=get_duration_keyboard())
    
    @router.callback_query(F.data.startswith("duration:"), MultiBookingStates.choosing_duration)
    async def multi_duration_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор длительности для мультиброни"""
        await callback.answer()
        duration = int(callback.data.split(":")[1])
        
        data = await state.get_data()
        start_time = data.get("start_time", 0)
        
        end_hour = start_time + (duration // 60)
        if end_hour > Config.WORK_HOURS_END:
            await callback.message.edit_text(
                f"❌ Аренда закончится после {Config.WORK_HOURS_END}:00. Выберите меньшую длительность.",
                reply_markup=get_duration_keyboard()
            )
            return
        
        await state.update_data(duration=duration)
        
        # Для мультиброни используем количество 1 по умолчанию для каждой доски
        selected_board_ids = data.get("selected_board_ids", [])
        board_quantities = {board_id: 1 for board_id in selected_board_ids}
        await state.update_data(board_quantities=board_quantities)
        await state.set_state(MultiBookingStates.confirming)
        
        # Показываем подтверждение
        booking_date_str = data.get("booking_date")
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        
        boards_data = []
        total_amount = 0
        
        for board_id in selected_board_ids:
            board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
            if not board:
                continue
            
            quantity = board_quantities.get(board_id, 1)
            hours = duration / 60.0
            amount = board['price'] * hours * quantity
            total_amount += amount
            
            boards_data.append({
                'id': board_id,
                'name': board['name'],
                'price': board['price'],
                'quantity': quantity,
                'amount': amount,
                'partner_id': board.get('partner_id')
            })
        
        text = f"🎯 <b>Подтверждение мультиброни</b>\n\n"
        text += f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {start_time}:{start_minute:02d}\n"
        text += f"⏱ Длительность: {duration} минут\n\n"
        text += "<b>Выбранные доски:</b>\n"
        
        for board in boards_data:
            text += f"• {board['name']} x{board['quantity']} = {board['amount']:.2f}₽\n"
        
        text += f"\n💰 <b>Итого: {total_amount:.2f}₽</b>"
        
        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="multi:confirm")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="multi:back_to_boards")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    async def _multi_show_confirm(callback: CallbackQuery, state: FSMContext, db: Database):
        """Подтверждение мультиброни"""
        data = await state.get_data()
        selected_board_ids = data.get("selected_board_ids", [])
        booking_date_str = data.get("booking_date")
        start_time = data.get("start_time")
        start_minute = data.get("start_minute", 0)
        duration = data.get("duration")
        board_quantities = data.get("board_quantities", {})
        
        if not selected_board_ids:
            await callback.message.edit_text("❌ Ошибка: не выбраны доски.")
            return
        
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        
        # Получаем информацию о досках
        boards_data = []
        total_amount = 0
        
        for board_id in selected_board_ids:
            board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
            if not board:
                continue
            
            quantity = board_quantities.get(board_id, 1)
            hours = duration / 60.0
            amount = board['price'] * hours * quantity
            total_amount += amount
            
            boards_data.append({
                'id': board_id,
                'name': board['name'],
                'price': board['price'],
                'quantity': quantity,
                'amount': amount,
                'partner_id': board.get('partner_id')
            })
        
        text = f"🎯 <b>Подтверждение мультиброни</b>\n\n"
        text += f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {start_time}:{start_minute:02d}\n"
        text += f"⏱ Длительность: {duration} минут\n\n"
        text += "<b>Выбранные доски:</b>\n"
        
        for board in boards_data:
            text += f"• {board['name']} x{board['quantity']} = {board['amount']:.2f}₽\n"
        
        text += f"\n💰 <b>Итого: {total_amount:.2f}₽</b>"
        
        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="multi:confirm")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="multi:back_to_boards")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "multi:confirm", MultiBookingStates.confirming)
    async def multi_confirm_create(callback: CallbackQuery, state: FSMContext):
        """Создание мультиброни"""
        await callback.answer()
        data = await state.get_data()
        selected_board_ids = data.get("selected_board_ids", [])
        booking_date_str = data.get("booking_date")
        start_time = data.get("start_time")
        start_minute = data.get("start_minute", 0)
        duration = data.get("duration")
        board_quantities = data.get("board_quantities", {})
        user_id = callback.from_user.id
        
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        
        # Генерируем group_id (используем timestamp)
        import time
        group_id = int(time.time())
        
        booking_ids = []
        total_amount = 0
        
        # Проверяем доступность всех досок
        for board_id in selected_board_ids:
            board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
            if not board:
                continue
            
            quantity = board_quantities.get(board_id, 1)
            
            # Проверка доступности
            is_available = await booking_service.check_board_availability(
                board_id, booking_date, start_time, start_minute, duration, quantity
            )
            
            if not is_available:
                await callback.message.edit_text(
                    f"❌ Доска '{board['name']}' недоступна на выбранное время.\n"
                    "Попробуйте выбрать другое время или убрать эту доску.",
                    reply_markup=get_back_keyboard("multi:back_to_boards")
                )
                return
        
        # Создаем бронирования для каждой доски
        try:
            for board_id in selected_board_ids:
                board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
                if not board:
                    continue
                
                quantity = board_quantities.get(board_id, 1)
                hours = duration / 60.0
                amount = board['price'] * hours * quantity
                total_amount += amount
                
                # Создаем бронирование с group_id
                cursor = await db.execute(
                    """INSERT INTO bookings 
                       (user_id, board_id, board_name, date, start_time, start_minute, 
                        duration, quantity, amount, status, partner_id, group_id, payment_deadline)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, board_id, board['name'], booking_date, start_time, start_minute,
                        duration, quantity, amount, "waiting_partner", board.get('partner_id'),
                        group_id, datetime.now() + timedelta(minutes=Config.PAYMENT_TIMEOUT_MINUTES)
                    )
                )
                booking_ids.append(cursor.lastrowid)
            
            # Сохраняем данные для оплаты
            await state.update_data(
                booking_ids=booking_ids,
                group_id=group_id,
                total_amount=total_amount
            )
            await state.set_state(MultiBookingStates.choosing_payment)
            
            # Переходим к выбору способа оплаты
            from handlers.payment_handlers import get_payment_method_keyboard
            text = f"✅ <b>Мультибронь создана!</b>\n\n"
            text += f"Создано бронирований: {len(booking_ids)}\n"
            text += f"💰 Сумма к оплате: {total_amount:.2f}₽\n\n"
            text += "Выберите способ оплаты:"
            
            try:
                await callback.message.edit_text(text, reply_markup=get_payment_method_keyboard())
            except:
                await callback.message.answer(text, reply_markup=get_payment_method_keyboard())
                
        except Exception as e:
            logger.error(f"Error creating multi-booking: {e}")
            await callback.message.edit_text("❌ Ошибка при создании мультиброни. Попробуйте еще раз.")
    
    @router.callback_query(F.data == "multi:back_to_boards", MultiBookingStates.confirming)
    async def multi_back_to_boards(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору досок"""
        await callback.answer()
        await state.set_state(MultiBookingStates.choosing_boards)
        data = await state.get_data()
        location_id = data.get("location_id")
        
        if location_id:
            boards = await db.fetchall(
                """SELECT * FROM boards 
                   WHERE location_id = ? AND is_active = 1 
                   ORDER BY name""",
                (location_id,)
            )
            
            location = await db.fetchone("SELECT name FROM locations WHERE id = ?", (location_id,))
            text = f"🎯 <b>Мультибронь</b>\n\n"
            text += f"📍 Локация: {location['name']}\n\n"
            text += "Выберите доски (можно выбрать несколько):"
            
            buttons = []
            selected_board_ids = data.get("selected_board_ids", [])
            
            for board in boards[:20]:
                is_selected = board['id'] in selected_board_ids
                prefix = "✅" if is_selected else "⬜"
                buttons.append([InlineKeyboardButton(
                    text=f"{prefix} {board['name']} - {board['price']:.0f}₽/ч",
                    callback_data=f"multi:board_toggle:{board['id']}"
                )])
            
            buttons.append([InlineKeyboardButton(text="➡️ Далее", callback_data="multi:next")])
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="booking_type:multi")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            if selected_board_ids:
                text += f"\n\nВыбрано досок: {len(selected_board_ids)}"
            
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
    

