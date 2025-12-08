import logging
from database import init_db, get_booked_slots, save_booking, get_user_bookings, cancel_booking, get_booking_by_order_id
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import asyncio


# --- 1. Настройка FSM ---
class BookingStates(StatesGroup):
    CHOOSING_BOARD = State()
    CHOOSING_DAY = State()
    CHOOSING_DURATION = State()
    CHOOSING_TIME = State()
    CONFIRMING = State()


# --- 2. Инициализация бота ---
bot = Bot(token="8089089145:AAGRaiDp_cW45TxW_ZbVO568jpA5pBRF0aU",
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- 3. Константы ---
WORKING_HOURS = list(range(9, 21))  # Часы работы с 9:00 до 21:00
MIN_DURATION = 1  # Минимальная продолжительность (час)
MAX_DURATION = 8  # Максимальная продолжительность (часов)
ADMIN_CHAT_ID = 202140267
SUPPORT_CHAT = "@supclub_support"


# --- 4. Клавиатуры ---
def get_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Быстрое бронирование")],
            [KeyboardButton(text="📋 Мои бронирования")],
            [KeyboardButton(text="💰 Тарифы"), KeyboardButton(text="📞 Контакты")]
        ],
        resize_keyboard=True
    )


def get_back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True
    )


def get_days_kb():
    days = []
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(0, 5):
        day = today + timedelta(days=i)
        days.append([KeyboardButton(text=day.strftime("%d.%m (%a)"))])
    days.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=days, resize_keyboard=True)


def get_duration_kb():
    durations = []
    for i in range(MIN_DURATION, MAX_DURATION + 1):
        durations.append([KeyboardButton(text=f"{i} час{'а' if 2 <= i <= 4 else 'ов'}")])
    durations.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=durations, resize_keyboard=True)


async def get_times_kb(selected_day: str, duration: int):
    times = []
    try:
        day_str = selected_day.split()[0]
        selected_date = datetime.strptime(day_str, "%d.%m").replace(
            year=datetime.now().year,
            hour=0, minute=0, second=0, microsecond=0
        )

        booked_slots = await get_booked_slots(selected_date.date())

        for hour in WORKING_HOURS:
            end_hour = hour + duration
            if end_hour > WORKING_HOURS[-1] + 1:
                continue

            is_available = True
            for slot in booked_slots:
                if hour < slot['end_hour'] and end_hour > slot['start_hour']:
                    is_available = False
                    break

            time_str = f"{hour:02d}:00"
            times.append([KeyboardButton(text=time_str, disabled=not is_available)])

    except Exception as e:
        logging.error(f"Ошибка формирования времени: {e}")
        times = [[KeyboardButton(text="Ошибка загрузки времени")]]

    times.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=times, resize_keyboard=True)


def get_booking_kb(booking_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{booking_id}"),
            InlineKeyboardButton(text="🔄 Перенести", callback_data=f"reschedule_{booking_id}")
        ],
        [
            InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_CHAT),
            InlineKeyboardButton(text="🔙 Назад", callback_data="my_bookings")
        ]
    ])


def get_bookings_list_kb(bookings: list):
    keyboard = []
    for i, booking in enumerate(bookings, 1):
        keyboard.append([
            InlineKeyboardButton(
                text=f"#{i} {booking['date']} {booking['time']}",
                callback_data=f"booking_{booking['order_id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- 5. Основные команды ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏄 Добро пожаловать в SUP-клуб!\nВыберите действие:",
        reply_markup=get_main_kb()
    )


@dp.message(Command("mybookings"))
@dp.message(F.text == "📋 Мои бронирования")
async def cmd_mybookings(message: types.Message):
    bookings = await get_user_bookings(message.from_user.id)

    if not bookings:
        await message.answer("📭 У вас нет активных бронирований", reply_markup=get_main_kb())
        return

    text = "📅 <b>Ваши активные бронирования:</b>\n\nНажмите на бронь для управления:"
    await message.answer(text, reply_markup=get_bookings_list_kb(bookings))


@dp.callback_query(F.data.startswith("booking_"))
async def show_booking_details(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    booking = await get_booking_by_order_id(order_id)

    if not booking:
        await callback.answer("Бронь не найдена")
        return

    end_hour = int(booking['time'].split(':')[0]) + booking['duration']
    end_time = f"{end_hour:02d}:00"

    text = (
        f"🏄 <b>Бронь #{booking['order_id']}</b>\n\n"
        f"• Тип доски: {booking['board_type']}\n"
        f"• Дата: {booking['date']}\n"
        f"• Время: {booking['time']}-{end_time}\n"
        f"• Продолжительность: {booking['duration']} ч\n"
        f"• Стоимость: {booking['total_price']} руб\n"
        f"• Статус: {booking['status']}"
    )

    await callback.message.edit_text(text, reply_markup=get_booking_kb(booking['order_id']))
    await callback.answer()


@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_handler(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel_{order_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"booking_{order_id}")
        ]
    ])

    await callback.message.edit_text(
        "❓ Вы уверены, что хотите отменить бронирование?",
        reply_markup=confirm_kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[2]

    if await cancel_booking(order_id):
        await callback.message.edit_text(
            f"✅ Бронь #{order_id} успешно отменена",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Мои брони", callback_data="my_bookings")]
            ])
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось отменить бронирование",
            reply_markup=get_booking_kb(order_id)
        )
    await callback.answer()


@dp.callback_query(F.data == "my_bookings")
async def back_to_bookings(callback: types.CallbackQuery):
    await cmd_mybookings(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=None
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_kb()
    )
    await callback.answer()


@dp.message(F.text == "🔙 Назад")
async def handle_back(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == BookingStates.CHOOSING_DAY:
        await state.set_state(BookingStates.CHOOSING_BOARD)
        await start_booking(message, state)
    elif current_state == BookingStates.CHOOSING_DURATION:
        await state.set_state(BookingStates.CHOOSING_DAY)
        data = await state.get_data()
        await message.answer("📅 Выберите день:", reply_markup=get_days_kb())
    elif current_state == BookingStates.CHOOSING_TIME:
        await state.set_state(BookingStates.CHOOSING_DURATION)
        await message.answer("⏳ Выберите продолжительность аренды:", reply_markup=get_duration_kb())
    elif current_state == BookingStates.CONFIRMING:
        await state.set_state(BookingStates.CHOOSING_TIME)
        data = await state.get_data()
        await message.answer("⏰ Выберите время начала:", reply_markup=await get_times_kb(data['day'], data['duration']))
    else:
        await state.clear()
        await message.answer("Главное меню:", reply_markup=get_main_kb())


# --- 6. Обработчики бронирования ---
@dp.message(F.text == "🚀 Быстрое бронирование")
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingStates.CHOOSING_BOARD)
    await message.answer(
        "Выберите тип доски:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🟢 Standard (1000 руб/час)")],
                [KeyboardButton(text="🔵 Touring (1500 руб/час)")],
                [KeyboardButton(text="🔴 Race (2000 руб/час)")],
                [KeyboardButton(text="🔙 Назад")]
            ],
            resize_keyboard=True
        )
    )


@dp.message(
    BookingStates.CHOOSING_BOARD,
    F.text.regexp(r'^(🟢 Standard|🔵 Touring|🔴 Race) \(\d+ руб/час\)$')
)
async def choose_board(message: types.Message, state: FSMContext):
    board_type = message.text.split()[0]
    price = int(message.text.split('(')[1].split()[0])
    await state.update_data(board_type=board_type, price=price)
    await state.set_state(BookingStates.CHOOSING_DAY)
    await message.answer("📅 Выберите день:", reply_markup=get_days_kb())


@dp.message(BookingStates.CHOOSING_DAY)
async def choose_day(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await handle_back(message, state)
        return

    try:
        day_str = message.text.split()[0]
        selected_date = datetime.strptime(day_str, "%d.%m").replace(
            year=datetime.now().year
        )
        if selected_date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            await message.answer("❌ Нельзя выбрать прошедшую дату. Пожалуйста, выберите другую дату.")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, выберите дату из предложенных вариантов.")
        return

    await state.update_data(day=message.text)
    await state.set_state(BookingStates.CHOOSING_DURATION)
    await message.answer("⏳ Выберите продолжительность аренды:", reply_markup=get_duration_kb())


@dp.message(BookingStates.CHOOSING_DURATION)
async def choose_duration(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await handle_back(message, state)
        return

    try:
        duration = int(message.text.split()[0])
        if not MIN_DURATION <= duration <= MAX_DURATION:
            raise ValueError
    except ValueError:
        await message.answer(f"❌ Пожалуйста, выберите продолжительность от {MIN_DURATION} до {MAX_DURATION} часов.")
        return

    await state.update_data(duration=duration)
    data = await state.get_data()
    await state.set_state(BookingStates.CHOOSING_TIME)
    await message.answer("⏰ Выберите время начала:", reply_markup=await get_times_kb(data['day'], duration))


@dp.message(BookingStates.CHOOSING_TIME)
async def choose_time(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await handle_back(message, state)
        return

    try:
        hour = int(message.text.split(':')[0])
        if hour not in WORKING_HOURS:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, выберите время из предложенных вариантов.")
        return

    await state.update_data(time=message.text)
    data = await state.get_data()
    total = data['price'] * data['duration']

    end_hour = int(data['time'].split(':')[0]) + data['duration']
    end_time = f"{end_hour:02d}:00"

    await message.answer(
        f"🔍 <b>Ваш выбор:</b>\n\n"
        f"• Доска: {data['board_type']}\n"
        f"• Дата: {data['day']}\n"
        f"• Время: {data['time']}-{end_time}\n"
        f"• Продолжительность: {data['duration']} ч\n"
        f"• Стоимость: {total} руб\n\n"
        "Нажмите '✅ Подтвердить' для завершения",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Подтвердить")],
                [KeyboardButton(text="🔄 Начать заново")],
                [KeyboardButton(text="🔙 Назад")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(BookingStates.CONFIRMING)


@dp.message(BookingStates.CONFIRMING, F.text == "✅ Подтвердить")
async def confirm_booking(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = f"SUP-{datetime.now().strftime('%d%m%H%M')}-{message.from_user.id}"
    total_price = data['price'] * data['duration']

    await save_booking(
        order_id=order_id,
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name,
        board_type=data['board_type'],
        date=data['day'],
        time=data['time'],
        duration=data['duration'],
        total_price=total_price,
        status="confirmed"
    )

    end_hour = int(data['time'].split(':')[0]) + data['duration']
    end_time = f"{end_hour:02d}:00"

    await message.answer(
        f"🎉 <b>Бронь #{order_id} подтверждена!</b>\n\n"
        f"<b>Детали:</b>\n"
        f"• Доска: {data['board_type']}\n"
        f"• Дата: {data['day']}\n"
        f"• Время: {data['time']}-{end_time}\n"
        f"• Продолжительность: {data['duration']} ч\n"
        f"• Сумма: {total_price} руб\n\n"
        f"📞 Поддержка: {SUPPORT_CHAT}\n"
        "Сохраните это сообщение как чек",
        reply_markup=get_main_kb()
    )

    admin_text = (
        f"🚀 <b>НОВАЯ БРОНЬ #{order_id}</b>\n\n"
        f"👤 <b>Клиент:</b> <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
        f"📱 @{message.from_user.username or 'нет'}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"📅 <b>Дата:</b> {data['day']}\n"
        f"⏰ <b>Время:</b> {data['time']}-{end_time}\n"
        f"🏄 <b>Доска:</b> {data['board_type']}\n"
        f"⏳ <b>Продолжительность:</b> {data['duration']} ч\n"
        f"💵 <b>Сумма:</b> {total_price} руб\n\n"
        f"#заказ_{order_id}"
    )

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать клиенту",
                    url=f"tg://user?id={message.from_user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить бронь",
                    callback_data=f"cancel_{order_id}"
                )
            ]
        ])
    )

    await state.clear()


@dp.message(F.text == "🔄 Начать заново")
async def restart_booking(message: types.Message, state: FSMContext):
    await state.clear()
    await start_booking(message, state)


# --- 7. Обработчики меню ---
@dp.message(F.text == "💰 Тарифы")
async def show_prices(message: types.Message):
    await message.answer(
        "💰 <b>Наши тарифы:</b>\n\n"
        "🟢 Standard - 1000 руб/час\n"
        "🔵 Touring - 1500 руб/час\n"
        "🔴 Race - 2000 руб/час\n\n"
        f"Доступная продолжительность: от {MIN_DURATION} до {MAX_DURATION} часов"
    )


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: types.Message):
    await message.answer(
        "📞 <b>Наши контакты:</b>\n\n"
        f"Телеграм: {SUPPORT_CHAT}\n"
        "Телефон: +7 (XXX) XXX-XX-XX\n"
        "Адрес: г. Москва, ул. Примерная, 123"
    )


# --- 8. Обработка неизвестных команд ---
@dp.message()
async def handle_unknown(message: types.Message):
    await message.answer(
        "Пожалуйста, используйте кнопки меню",
        reply_markup=get_main_kb()
    )


# --- 9. Запуск бота ---
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())