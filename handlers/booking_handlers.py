# handlers/booking_handlers.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import new_main_menu
from handlers.choose_location import show_locations_on_map  # ваш хэндлер, который рисует точки
# Импорт ваших клавиатур для бронирования:
from handlers.booking_keyboards import (
    booking_choice_keyboard,
    dates_keyboard,
    duration_keyboard,
    time_slots_keyboard,
    quantity_keyboard,
    confirm_booking_keyboard,
)

booking_router = Router()


class BookingStates(StatesGroup):
    choosing_location = State()
    choosing_mode     = State()
    choosing_board    = State()
    choosing_date     = State()
    choosing_duration = State()
    choosing_time     = State()
    choosing_qty      = State()


def register_booking_handlers(router: Router, db):

    @router.message(F.text == "🏄 Новая бронь")
    async def start_booking(msg: types.Message, state: FSMContext):
        await state.clear()
        # 1) Показываем карту с локациями
        await show_locations_on_map(msg)
        await state.set_state(BookingStates.choosing_location)

    @router.callback_query(BookingStates.choosing_location, F.data.startswith("loc_"))
    async def location_chosen(cq: types.CallbackQuery, state: FSMContext):
        loc_id = int(cq.data.split("_")[1])
        await state.update_data(location_id=loc_id)
        # 2) Просим выбрать режим
        await cq.message.answer("Выберите тип бронирования:", reply_markup=booking_choice_keyboard())
        await state.set_state(BookingStates.choosing_mode)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_mode, F.data.startswith("mode:"))
    async def mode_chosen(cq: types.CallbackQuery, state: FSMContext):
        mode = cq.data.split(":")[1]  # instant, regular, daily
        await state.update_data(mode=mode)

        data = await state.get_data()
        loc_id = data["location_id"]

        # сразу предложим список досок в этой локации
        boards = await db.execute(
            "SELECT id, name FROM boards WHERE location_id=? AND is_active=1",
            (loc_id,), fetchall=True
        )
        if not boards:
            return await cq.message.answer("❌ В этой локации нет доступных досок.", reply_markup=new_main_menu())

        kb = InlineKeyboardBuilder()
        for bid, name in boards:
            kb.button(text=name, callback_data=f"board_{bid}")
        kb.adjust(1)
        await cq.message.answer("Выберите доску:", reply_markup=kb.as_markup())
        await state.set_state(BookingStates.choosing_board)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_board, F.data.startswith("board_"))
    async def board_chosen(cq: types.CallbackQuery, state: FSMContext):
        board_id = int(cq.data.split("_")[1])
        await state.update_data(board_id=board_id)
        # 3) Даты
        kb = await dates_keyboard()
        await cq.message.answer("Выберите дату:", reply_markup=kb)
        await state.set_state(BookingStates.choosing_date)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_date, F.data.startswith("date_"))
    async def date_chosen(cq: types.CallbackQuery, state: FSMContext):
        date = cq.data.split("_",1)[1]
        await state.update_data(date=date)
        # 4) Длительность
        kb = await duration_keyboard()
        await cq.message.answer("Выберите длительность (часы):", reply_markup=kb)
        await state.set_state(BookingStates.choosing_duration)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_duration, F.data.startswith("dur_h_"))
    async def dur_chosen(cq: types.CallbackQuery, state: FSMContext):
        dur = int(cq.data.split("_")[2])
        await state.update_data(duration=dur)
        # 5) Слоты времени
        data = await state.get_data()
        kb = await time_slots_keyboard(db, data["date"], data["board_id"], dur)
        await cq.message.answer("Выберите время:", reply_markup=kb)
        await state.set_state(BookingStates.choosing_time)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_time, F.data.startswith("time_"))
    async def time_chosen(cq: types.CallbackQuery, state: FSMContext):
        start_hour = int(cq.data.split("_")[1])
        await state.update_data(start_hour=start_hour)
        # 6) Количество
        data = await state.get_data()
        kb = await quantity_keyboard(db, data["board_id"], data["date"], start_hour, data["duration"])
        await cq.message.answer("Выберите количество досок:", reply_markup=kb)
        await state.set_state(BookingStates.choosing_qty)
        await cq.answer()

    @router.callback_query(BookingStates.choosing_qty, F.data.startswith("qty_"))
    async def qty_chosen(cq: types.CallbackQuery, state: FSMContext):
        qty = int(cq.data.split("_")[1])
        await state.update_data(qty=qty)
        # 7) Подтверждение
        kb = confirm_booking_keyboard()
        await cq.message.answer("Подтвердите бронь:", reply_markup=kb)
        await state.set_state(None)  # или введите своё ConfirmState
        await cq.answer()

    @router.callback_query(F.data.startswith("confirm_booking_"))
    async def _confirm_booking(cq: types.CallbackQuery):
        oid = int(cq.data.split("_")[-1])
        await cq.answer()
        await db.execute(
            "UPDATE bookings SET status='active' WHERE id=? AND status IN ('waiting_partner','waiting_card','waiting_cash')",
            (oid,), commit=True
        )
        await cq.message.answer(f"✅ Бронь #{oid} подтверждена и активирована.")

    @router.callback_query(F.data == "cancel_booking")
    async def cancel_booking(cq: types.CallbackQuery, state: FSMContext):
        await cq.message.answer("❌ Бронирование отменено.", reply_markup=new_main_menu())
        await state.clear()
        await cq.answer()

# Регистрируем
def setup(dp: Router, db):
    register_booking_handlers(dp, db)
    dp.include_router(booking_router)
