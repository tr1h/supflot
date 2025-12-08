import logging

from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import OPENWEATHER_KEY
from services.weather_service import get_weather
from services.booking_service import BookingService
from services.payment_service import PaymentService
from services.notification_service import NotificationService
from keyboards.booking import (
    main_menu_kb,
    dates_kb,
    duration_kb,
    payment_kb,
    confirm_kb,
)

logger = logging.getLogger(__name__)
booking_router = Router()

class BookingStates(StatesGroup):
    select_location = State()
    select_board = State()
    select_date = State()
    select_duration = State()
    select_time = State()
    select_quantity = State()
    confirm_amount = State()
    select_payment = State()

@booking_router.message(F.text == "🏄 Новая бронь")
async def new_booking(message: types.Message, state: FSMContext):
    """Начало FSM‑потока: выбор локации."""
    await state.clear()
    locs = await BookingService.list_locations(message.bot.db)
    kb = InlineKeyboardBuilder()
    for loc_id, name, address, lat, lon in locs:
        kb.button(text=f"📍 {name}", callback_data=f"loc_{loc_id}")
    kb.adjust(2)
    await message.answer("Выберите локацию:", reply_markup=kb.as_markup())
    await state.set_state(BookingStates.select_location)

@booking_router.callback_query(StateFilter(BookingStates.select_location), F.data.startswith("loc_"))
async def select_location(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора локации: показываем погоду и доски."""
    await cq.answer()
    loc_id = int(cq.data.split("_", 1)[1])
    await state.update_data(location_id=loc_id)

    # данные локации + погода
    name, address, lat, lon = await BookingService.get_location(cq.bot.db, loc_id)
    weather = await get_weather(lat, lon, OPENWEATHER_KEY)
    await cq.message.answer(
        f"📍 <b>{name}</b>\n{address}\n{weather}",
        parse_mode="HTML"
    )

    # список досок
    boards = await BookingService.list_boards(cq.bot.db, loc_id)
    kb = InlineKeyboardBuilder()
    for bid, bname, total, price, desc in boards:
        kb.button(
            text=f"🛶 {bname} — {price}₽/ч (Своб. {total})",
            callback_data=f"board_{bid}"
        )
    kb.adjust(1)
    await cq.message.answer("Выберите доску:", reply_markup=kb.as_markup())
    await state.set_state(BookingStates.select_board)

@booking_router.callback_query(StateFilter(BookingStates.select_board), F.data.startswith("board_"))
async def select_board(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора доски: показываем описание и дату."""
    await cq.answer()
    bid = int(cq.data.split("_", 1)[1])
    await state.update_data(board_id=bid)

    board = await BookingService.get_board(cq.bot.db, bid)
    await state.update_data(
        board_name=board['name'],
        price=board['price'],
        description=board['description']
    )
    await cq.message.answer(
        f"🛶 <b>{board['name']}</b>\n{board['description']}\nЦена: {board['price']}₽/ч",
        parse_mode="HTML"
    )
    await cq.message.answer("📅 Выберите дату:", reply_markup=dates_kb())
    await state.set_state(BookingStates.select_date)

@booking_router.callback_query(StateFilter(BookingStates.select_date), F.data.startswith("date_"))
async def select_date(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора даты: показываем длительность."""
    await cq.answer()
    date = cq.data.split("_", 1)[1]
    await state.update_data(date=date)
    await cq.message.answer("⏳ Выберите длительность:", reply_markup=duration_kb())
    await state.set_state(BookingStates.select_duration)

@booking_router.callback_query(StateFilter(BookingStates.select_duration), F.data.startswith("dur_"))
async def select_duration(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора длительности: показываем слоты времени."""
    await cq.answer()
    duration = int(cq.data.split("_", 1)[1])
    await state.update_data(duration=duration)

    data = await state.get_data()
    slots = await BookingService.compute_slots(
        cq.bot.db,
        board_id=data['board_id'],
        date=data['date'],
        duration=duration
    )
    kb = InlineKeyboardBuilder()
    for slot in slots:
        start = slot['start']
        free  = slot['free']
        if free <= 0:
            continue
        label = f"{start:02}:00–{(start+duration)%24:02}:00 ({free})"
        kb.button(text=label, callback_data=f"time_{start}")
    kb.adjust(2)
    await cq.message.answer("⏰ Выберите время:", reply_markup=kb.as_markup())
    await state.set_state(BookingStates.select_time)

@booking_router.callback_query(StateFilter(BookingStates.select_time), F.data.startswith("time_"))
async def select_time(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора времени: спрашиваем количество досок."""
    await cq.answer()
    start_time = int(cq.data.split("_", 1)[1])
    await state.update_data(start_time=start_time)

    data = await state.get_data()
    max_qty = await BookingService.get_max_quantity(
        cq.bot.db,
        board_id=data['board_id'],
        date=data['date'],
        start=start_time,
        duration=data['duration']
    )
    kb = InlineKeyboardBuilder()
    for q in range(1, min(max_qty, 4) + 1):
        kb.button(text=str(q), callback_data=f"qty_{q}")
    kb.adjust(4)
    await cq.message.answer(
        f"Сколько досок? (макс {min(max_qty,4)})",
        reply_markup=kb.as_markup()
    )
    await state.set_state(BookingStates.select_quantity)

@booking_router.callback_query(StateFilter(BookingStates.select_quantity), F.data.startswith("qty_"))
async def select_quantity(cq: types.CallbackQuery, state: FSMContext):
    """Обработка выбора количества: показываем итог и кнопку подтверждения."""
    await cq.answer()
    quantity = int(cq.data.split("_", 1)[1])
    await state.update_data(quantity=quantity)

    data = await state.get_data()
    amount = data['price'] * data['duration'] * quantity
    await state.update_data(amount=amount)

    summary = BookingService.format_summary({
        'board_name': data['board_name'],
        'date': data['date'],
        'start': data['start_time'],
        'duration': data['duration'],
        'quantity': quantity,
        'amount': amount
    })
    await cq.message.answer(
        summary,
        parse_mode="HTML",
        reply_markup=confirm_kb()
    )
    await state.set_state(BookingStates.confirm_amount)

@booking_router.callback_query(StateFilter(BookingStates.confirm_amount), F.data == "confirm_booking")
async def confirm_amount(cq: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения брони: переходим к оплате."""
    await cq.answer()
    await cq.message.answer(
        "Спасибо! Выберите способ оплаты:",
        reply_markup=payment_kb()
    )
    await state.set_state(BookingStates.select_payment)

@booking_router.callback_query(StateFilter(BookingStates.select_payment), F.data.startswith("pay_"))
async def process_payment(cq: types.CallbackQuery, state: FSMContext):
    """Запуск оплаты через PaymentService и очистка состояния."""
    await cq.answer()
    method = cq.data.split("_", 1)[1]
    data = await state.get_data()
    booking_id = await PaymentService.start_payment(
        bot=cq.bot,
        chat_id=cq.from_user.id,
        booking_data=data,
        payment_method=method
    )
    # уведомляем админов о новой броне
    summary = BookingService.format_summary(data)
    await NotificationService.new_booking(cq.bot, booking_id, summary)

    await state.clear()

__all__ = ["booking_router"]
