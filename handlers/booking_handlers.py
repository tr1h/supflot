"""Обработчики бронирований"""
import logging
from datetime import date, datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from services.booking_service import BookingService
from keyboards.user import (
    get_booking_type_keyboard, get_locations_keyboard, get_boards_keyboard,
    get_payment_method_keyboard, get_back_keyboard, get_time_keyboard,
    get_duration_keyboard, get_quantity_keyboard, get_date_keyboard
)
from utils.date_parser import parse_date, is_date_valid
from config import Config

logger = logging.getLogger(__name__)


class BookingStates(StatesGroup):
    """Состояния для процесса бронирования"""
    choosing_location = State()
    choosing_board = State()
    choosing_date = State()
    choosing_time = State()
    choosing_duration = State()
    choosing_quantity = State()
    choosing_payment = State()


def register_booking_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков бронирований"""
    booking_service = BookingService(db)
    
    # Создаем notification_service если bot передан
    notification_service = None
    if bot:
        from notifications.notification_service import NotificationService
        notification_service = NotificationService(bot, db)
    
    @router.message(F.text == "🆕 Новая бронь")
    async def new_booking(message: Message, state: FSMContext):
        """Начало процесса бронирования"""
        text = "📅 <b>Выберите тип бронирования:</b>\n\n"
        text += "• <b>Обычная бронь</b> - бронирование на конкретную дату и время\n"
        text += "• <b>Мгновенная бронь</b> - бронирование на сегодня\n"
        text += "• <b>Суточная аренда</b> - аренда на сутки\n"
        text += "• <b>Мультибронь</b> - несколько досок одновременно"
        
        await message.answer(text, reply_markup=get_booking_type_keyboard())
    
    @router.callback_query(F.data == "booking_type:regular")
    async def booking_type_regular(callback: CallbackQuery, state: FSMContext):
        """Обычная бронь"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_location)
        await state.update_data(booking_type="regular")
        
        # Получаем активные локации
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        if not locations:
            await callback.message.edit_text(
                "❌ К сожалению, сейчас нет доступных локаций.\nПопробуйте позже.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
            return
        
        text = "📍 <b>Выберите локацию:</b>"
        await callback.message.edit_text(text, reply_markup=get_locations_keyboard(locations))
    
    @router.callback_query(F.data == "booking_type:instant")
    async def booking_type_instant(callback: CallbackQuery, state: FSMContext):
        """Мгновенная бронь - бронирование на сегодня"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_location)
        await state.update_data(booking_type="instant", booking_date=date.today().strftime("%Y-%m-%d"))
        
        # Получаем активные локации
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        if not locations:
            await callback.message.edit_text(
                "❌ К сожалению, сейчас нет доступных локаций.\nПопробуйте позже.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
            return
        
        text = "⚡ <b>Мгновенная бронь на сегодня</b>\n\n"
        text += "📍 <b>Выберите локацию:</b>"
        await callback.message.edit_text(text, reply_markup=get_locations_keyboard(locations))
    
    @router.callback_query(F.data == "booking_type:daily")
    async def booking_type_daily(callback: CallbackQuery, state: FSMContext):
        """Суточная аренда - аренда на полные сутки (24 часа)"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_location)
        await state.update_data(booking_type="daily")
        
        # Получаем активные локации
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        if not locations:
            await callback.message.edit_text(
                "❌ К сожалению, сейчас нет доступных локаций.\nПопробуйте позже.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
            return
        
        text = "🌙 <b>Суточная аренда</b>\n\n"
        text += "Аренда доски на полные 24 часа.\n\n"
        text += "📍 <b>Выберите локацию:</b>"
        await callback.message.edit_text(text, reply_markup=get_locations_keyboard(locations))
    
    @router.callback_query(F.data.startswith("location:"))
    async def location_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[1])
        await state.update_data(location_id=location_id)
        await state.set_state(BookingStates.choosing_board)
        
        # Получаем доски для локации
        boards = await db.fetchall(
            """SELECT * FROM boards 
               WHERE location_id = ? AND is_active = 1 
               ORDER BY name""",
            (location_id,)
        )
        
        if not boards:
            await callback.message.edit_text(
                "❌ В этой локации нет доступных досок.",
                reply_markup=get_back_keyboard("back_to_locations")
            )
            return
        
        location = await db.fetchone("SELECT name FROM locations WHERE id = ?", (location_id,))
        text = f"🏄 <b>Выберите доску для локации \"{location['name']}\":</b>"
        await callback.message.edit_text(text, reply_markup=get_boards_keyboard(boards))
    
    @router.callback_query(F.data.startswith("board:"))
    async def board_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[1])
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        data = await state.get_data()
        booking_type = data.get("booking_type", "regular")
        
        await state.update_data(board_id=board_id, board_price=board['price'], board_name=board['name'])
        
        # Получаем фото доски
        images = await db.fetchall(
            "SELECT file_id FROM board_images WHERE board_id = ? ORDER BY created_at LIMIT 1",
            (board_id,)
        )
        
        # Для мгновенной брони пропускаем выбор даты
        if booking_type == "instant":
            # Автоматически устанавливаем сегодняшнюю дату
            today = date.today()
            await state.update_data(booking_date=today.strftime("%Y-%m-%d"))
            await state.set_state(BookingStates.choosing_time)
            
            # Получаем доступные временные слоты на сегодня
            now = datetime.now()
            current_time_minutes = now.hour * 60 + now.minute
            available_slots = await booking_service.get_available_time_slots(
                board_id, today, duration=60, quantity=1, current_time_minutes=current_time_minutes
            )
            
            if not available_slots:
                text = f"⚡ <b>Мгновенная бронь</b>\n\n"
                text += f"Доска: {board['name']}\n"
                text += f"💰 Цена: {board['price']:.0f}₽/час\n\n"
                text += "❌ К сожалению, на сегодня нет доступных временных слотов для этой доски.\n"
                text += "Попробуйте выбрать другую доску или сделайте обычную бронь."
                await callback.message.edit_text(text, reply_markup=get_back_keyboard("back_to_boards"))
                return
            
            # Создаем клавиатуру с доступными временами
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            buttons = []
            for hour, minute in available_slots:
                buttons.append([InlineKeyboardButton(
                    text=f"{hour}:{minute:02d}",
                    callback_data=f"time:{hour}:{minute}"
                )])
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boards")])
            time_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            text = f"⚡ <b>Мгновенная бронь</b>\n\n"
            text += f"Доска: {board['name']}\n"
            if board.get('description'):
                text += f"{board['description']}\n\n"
            text += f"💰 Цена: {board['price']:.0f}₽/час\n"
            text += f"📅 Дата: {today.strftime('%d.%m.%Y')} (сегодня)\n\n"
            text += "⏰ <b>Выберите доступное время:</b>"
            
            if images and bot:
                try:
                    await bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=images[0]['file_id'],
                        caption=text,
                        reply_markup=time_keyboard
                    )
                    await callback.message.delete()
                    return
                except Exception as e:
                    logger.error(f"Error sending board photo: {e}")
            
            await callback.message.edit_text(text, reply_markup=time_keyboard)
            return
        
        # Для суточной аренды - выбираем дату (время можно пропустить, начнется с 00:00 или выбранное)
        if booking_type == "daily":
            await state.set_state(BookingStates.choosing_date)
            text = f"🌙 <b>Суточная аренда: {board['name']}</b>\n"
            if board.get('description'):
                text += f"{board['description']}\n\n"
            text += f"💰 Цена: {board['price']:.0f}₽/час × 24 часа = {board['price'] * 24:.0f}₽/сутки\n\n"
            text += "Выберите дату начала аренды:"
            
            if images and bot:
                try:
                    await bot.send_photo(
                        chat_id=callback.from_user.id,
                        photo=images[0]['file_id'],
                        caption=text,
                        reply_markup=get_date_keyboard()
                    )
                    await callback.message.delete()
                    return
                except Exception as e:
                    logger.error(f"Error sending board photo: {e}")
            
            await callback.message.edit_text(text, reply_markup=get_date_keyboard())
            return
        
        # Для обычной брони - выбираем дату
        await state.set_state(BookingStates.choosing_date)
        
        text = f"📅 <b>Доска: {board['name']}</b>\n"
        if board.get('description'):
            text += f"{board['description']}\n\n"
        text += f"💰 Цена: {board['price']:.0f}₽/час\n\n"
        text += "Выберите дату бронирования:"
        
        # Если есть фото, отправляем его с текстом
        if images and bot:
            try:
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=images[0]['file_id'],
                    caption=text,
                    reply_markup=get_date_keyboard()
                )
                await callback.message.delete()
                return
            except Exception as e:
                logger.error(f"Error sending board photo: {e}")
                # Если не удалось отправить фото, отправляем текст
                await callback.message.edit_text(text, reply_markup=get_date_keyboard())
        else:
            await callback.message.edit_text(text, reply_markup=get_date_keyboard())
    
    @router.callback_query(F.data == "back_to_locations")
    async def back_to_locations(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору локации"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_location)
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        text = "📍 <b>Выберите локацию:</b>"
        await callback.message.edit_text(text, reply_markup=get_locations_keyboard(locations))
    
    @router.callback_query(F.data == "back_to_boards")
    async def back_to_boards(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору досок"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_board)
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
            text = f"🏄 <b>Выберите доску для локации \"{location['name']}\":</b>"
            await callback.message.edit_text(text, reply_markup=get_boards_keyboard(boards))
    
    @router.callback_query(F.data.startswith("date:"), BookingStates.choosing_date)
    async def date_chosen(callback: CallbackQuery, state: FSMContext):
        """Обработка выбора даты"""
        await callback.answer()
        try:
            # callback.data = "date:2025-12-26"
            date_str = callback.data.split(":")[1]
            booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Валидация даты (не должно быть в прошлом)
            today = date.today()
            if booking_date < today:
                await callback.message.edit_text(
                    "❌ Нельзя выбрать дату в прошлом. Выберите другую дату.",
                    reply_markup=get_date_keyboard()
                )
                return
            
            data = await state.get_data()
            booking_type = data.get("booking_type", "regular")
            
            await state.update_data(booking_date=booking_date.strftime("%Y-%m-%d"))
            await state.set_state(BookingStates.choosing_time)
            
            # Для суточной аренды - особое сообщение
            if booking_type == "daily":
                text = f"🌙 <b>Суточная аренда</b>\n\n"
                text += f"📅 Дата начала: {booking_date.strftime('%d.%m.%Y')}\n"
                text += f"⏱ Длительность: 24 часа\n\n"
                text += "⏰ Выберите время начала (или используйте 00:00):"
            else:
                text = f"📅 <b>Дата: {booking_date.strftime('%d.%m.%Y')}</b>\n\n"
                text += "⏰ Выберите время начала аренды:"
            await callback.message.edit_text(text, reply_markup=get_time_keyboard())
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing date from callback data '{callback.data}': {e}")
            await callback.message.edit_text(
                "❌ Ошибка при выборе даты. Попробуйте еще раз.",
                reply_markup=get_date_keyboard()
            )
    
    @router.callback_query(F.data.startswith("time:"), BookingStates.choosing_time)
    async def time_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор времени"""
        await callback.answer()
        try:
            # callback.data = "time:8:0", после split(":") = ['time', '8', '0']
            parts = callback.data.split(":")
            if len(parts) < 2:
                raise ValueError("Invalid time format")
            hour = int(parts[1])
            minute = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing time from callback data '{callback.data}': {e}")
            await callback.message.edit_text(
                "❌ Ошибка при выборе времени. Попробуйте еще раз.",
                reply_markup=get_time_keyboard()
            )
            return
        
        data = await state.get_data()
        booking_date_str = data.get("booking_date")
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        
        # Проверка рабочего времени
        if hour < Config.WORK_HOURS_START or hour >= Config.WORK_HOURS_END:
            await callback.message.edit_text(
                f"❌ Время работы: {Config.WORK_HOURS_START}:00 - {Config.WORK_HOURS_END}:00",
                reply_markup=get_time_keyboard()
            )
            return
        
        booking_type = data.get("booking_type", "regular")
        
        await state.update_data(start_time=hour, start_minute=minute)
        
        # Для суточной аренды - фиксированная длительность 1440 минут (24 часа), пропускаем выбор длительности
        if booking_type == "daily":
            await state.update_data(duration=1440)  # 24 часа
            await state.set_state(BookingStates.choosing_quantity)
            
            board_price = data.get("board_price", 0)
            daily_amount = board_price * 24  # Стоимость за сутки
            
            text = f"🌙 <b>Суточная аренда</b>\n\n"
            text += f"⏰ Время начала: {hour}:{minute:02d}\n"
            text += f"⏱ Длительность: 24 часа\n"
            text += f"💰 Стоимость: {daily_amount:.0f}₽/сутки\n\n"
            text += "Выберите количество досок:"
            await callback.message.edit_text(text, reply_markup=get_quantity_keyboard())
        else:
            await state.set_state(BookingStates.choosing_duration)
            text = f"⏰ <b>Время начала: {hour}:{minute:02d}</b>\n\n"
            text += "⏱ Выберите длительность аренды:"
            await callback.message.edit_text(text, reply_markup=get_duration_keyboard())
    
    @router.callback_query(F.data == "back_to_date")
    async def back_to_date(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору даты"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_date)
        data = await state.get_data()
        board_name = data.get("board_name", "Доска")
        board_price = data.get("board_price", 0)
        
        text = f"📅 <b>Доска: {board_name}</b>\n"
        text += f"💰 Цена: {board_price:.0f}₽/час\n\n"
        text += "Выберите дату бронирования:"
        await callback.message.edit_text(text, reply_markup=get_date_keyboard())
    
    @router.callback_query(F.data.startswith("duration:"), BookingStates.choosing_duration)
    async def duration_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор длительности"""
        await callback.answer()
        duration = int(callback.data.split(":")[1])
        
        data = await state.get_data()
        start_time = data.get("start_time", 0)
        booking_date_str = data.get("booking_date")
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        
        # Проверка, что не выходим за рабочее время
        end_hour = start_time + (duration // 60)
        if end_hour > Config.WORK_HOURS_END:
            await callback.message.edit_text(
                f"❌ Аренда закончится после {Config.WORK_HOURS_END}:00. Выберите меньшую длительность.",
                reply_markup=get_duration_keyboard()
            )
            return
        
        await state.update_data(duration=duration)
        
        # Получаем доску для проверки доступного количества
        board_id = data.get("board_id")
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        max_quantity = board['quantity'] if board else 5
        
        await state.set_state(BookingStates.choosing_quantity)
        
        duration_text = f"{duration // 60} ч" if duration >= 60 else f"{duration} мин"
        text = f"⏱ <b>Длительность: {duration_text}</b>\n\n"
        text += f"📊 Выберите количество досок (доступно: {max_quantity}):"
        await callback.message.edit_text(text, reply_markup=get_quantity_keyboard(max_quantity))
    
    @router.callback_query(F.data == "back_to_time")
    async def back_to_time(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору времени"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_time)
        data = await state.get_data()
        booking_date_str = data.get("booking_date")
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        booking_type = data.get("booking_type", "regular")
        board_id = data.get("board_id")
        
        # Для мгновенной брони показываем только доступные временные слоты
        if booking_type == "instant" and board_id:
            now = datetime.now()
            current_time_minutes = now.hour * 60 + now.minute
            available_slots = await booking_service.get_available_time_slots(
                board_id, booking_date, duration=60, quantity=1, current_time_minutes=current_time_minutes
            )
            
            if available_slots:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                buttons = []
                for hour, minute in available_slots:
                    buttons.append([InlineKeyboardButton(
                        text=f"{hour}:{minute:02d}",
                        callback_data=f"time:{hour}:{minute}"
                    )])
                buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_boards")])
                time_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                
                text = f"⚡ <b>Мгновенная бронь</b>\n\n"
                text += f"📅 Дата: {booking_date.strftime('%d.%m.%Y')} (сегодня)\n\n"
                text += "⏰ <b>Выберите доступное время:</b>"
                await callback.message.edit_text(text, reply_markup=time_keyboard)
                return
        
        # Для обычной брони - стандартная клавиатура
        text = f"📅 <b>Дата: {booking_date.strftime('%d.%m.%Y')}</b>\n\n"
        text += "⏰ Выберите время начала аренды:"
        await callback.message.edit_text(text, reply_markup=get_time_keyboard())
    
    @router.callback_query(F.data.startswith("quantity:"), BookingStates.choosing_quantity)
    async def quantity_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор количества и завершение бронирования"""
        await callback.answer()
        quantity = int(callback.data.split(":")[1])
        
        data = await state.get_data()
        board_id = data.get("board_id")
        board_name = data.get("board_name")
        board_price = data.get("board_price")
        booking_date_str = data.get("booking_date")
        start_time = data.get("start_time")
        start_minute = data.get("start_minute", 0)
        duration = data.get("duration")
        
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        user_id = callback.from_user.id
        
        # Получаем информацию о доске и партнере
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        partner_id = board.get("partner_id")
        location_id = board.get("location_id")
        
        # Проверка доступности
        is_available = await booking_service.check_board_availability(
            board_id, booking_date, start_time, start_minute, duration, quantity
        )
        
        if not is_available:
            await callback.message.edit_text(
                "❌ Выбранное количество досок недоступно на это время. Попробуйте выбрать другое время или количество.",
                reply_markup=get_back_keyboard("back_to_duration")
            )
            return
        
        # Получаем тип бронирования
        booking_type = data.get("booking_type", "regular")
        
        # Расчет стоимости
        if booking_type == "daily":
            # Для суточной аренды: цена × 24 часа × количество
            amount = board_price * 24 * quantity
        else:
            # Для обычной аренды: цена × часы × количество
            hours = duration / 60.0
            amount = board_price * hours * quantity
        
        # Создание бронирования
        try:
            # Для мгновенной брони статус будет изменен после оплаты на 'active'
            initial_status = "waiting_partner" if booking_type != "instant" else "waiting_partner"
            
            booking_id = await booking_service.create_booking(
                user_id=user_id,
                board_id=board_id,
                board_name=board_name,
                booking_date=booking_date,
                start_time=start_time,
                start_minute=start_minute,
                duration=duration,
                quantity=quantity,
                amount=amount,
                partner_id=partner_id,
                status=initial_status
            )
            
            # Сохраняем booking_type для последующей проверки при оплате
            await state.update_data(booking_type=booking_type)
            
            await state.update_data(booking_id=booking_id, amount=amount)
            await state.set_state(BookingStates.choosing_payment)
            
            # Устанавливаем время истечения оплаты
            from config import Config
            payment_deadline = datetime.now() + timedelta(minutes=Config.PAYMENT_TIMEOUT_MINUTES)
            
            # Обновляем бронирование с временем истечения оплаты
            await db.execute(
                "UPDATE bookings SET payment_deadline = ? WHERE id = ?",
                (payment_deadline, booking_id)
            )
            
            # Форматируем время истечения для отображения
            deadline_str = payment_deadline.strftime("%H:%M")
            minutes_left = Config.PAYMENT_TIMEOUT_MINUTES
            
            # Формируем итоговую информацию
            text = "📋 <b>Подтверждение бронирования</b>\n\n"
            text += f"Доска: {board_name}\n"
            text += f"Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            text += f"Время: {start_time}:{start_minute:02d}\n"
            text += f"Длительность: {duration} мин\n"
            text += f"Количество: {quantity} шт.\n"
            text += f"💰 Сумма: {amount:.2f}₽\n\n"
            text += f"⏰ <b>Время на оплату: до {deadline_str} (осталось {minutes_left} мин)</b>\n\n"
            text += "Выберите способ оплаты:"
            
            await callback.message.edit_text(text, reply_markup=get_payment_method_keyboard())
            
            # Отправляем уведомления
            if notification_service and partner_id:
                try:
                    await notification_service.notify_partner_new_booking(partner_id, booking_id)
                    await notification_service.notify_admins_new_booking(booking_id)
                except Exception as e:
                    logger.error(f"Error sending notifications: {e}")
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            await callback.message.edit_text(
                "❌ Произошла ошибка при создании бронирования. Попробуйте еще раз.",
                reply_markup=get_back_keyboard("back_to_menu")
            )
    
    @router.callback_query(F.data == "back_to_duration")
    async def back_to_duration(callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору длительности"""
        await callback.answer()
        await state.set_state(BookingStates.choosing_duration)
        text = "⏱ Выберите длительность аренды:"
        await callback.message.edit_text(text, reply_markup=get_duration_keyboard())

