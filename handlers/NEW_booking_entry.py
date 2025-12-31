# handlers/NEW_booking_entry.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .NEW_states import NewBookingChoice
from .NEW_instant_booking import register_instant_booking, start_instant_booking  # ← добавили старт
from .NEW_regular_booking import start_regular_booking
from handlers.NEW_daily_booking_p2p import start_daily_booking_flow
from keyboards import booking_choice_keyboard, main_menu


def register_booking_entry(router: Router, db):
    """
    Точка входа в выбор типа бронирования + подключение сценариев.
    """
    # Регистрируем обработчики мгновенной аренды (их внутренние коллбеки)
    register_instant_booking(router, db)

    @router.message(F.text == "🏄 Новая бронь")
    async def entry(msg: Message, state: FSMContext):
        # чистим состояние и предлагаем выбрать режим
        await state.clear()
        await state.set_state(NewBookingChoice.choosing_mode)
        await msg.answer("Выберите тип бронирования:", reply_markup=booking_choice_keyboard())

    @router.callback_query(NewBookingChoice.choosing_mode, F.data.startswith("mode:"))
    async def mode_selected(cq: CallbackQuery, state: FSMContext):
        await cq.answer()
        mode = cq.data.split(":", 1)[1]

        if mode == "instant":
            # ЯВНО запускаем мгновенную аренду (не полагаемся на другие хендлеры)
            await start_instant_booking(cq.message, state, db)
            return

        if mode == "regular":
            # Классическая бронь по дате/времени
            await start_regular_booking(cq.message, state, db)
            return

        if mode == "daily":
            # Суточная аренда
            await start_daily_booking_flow(cq.message, state, db)
            return

        # отмена/фолбэк
        await state.clear()
        await cq.message.answer("Отменено.", reply_markup=main_menu())
