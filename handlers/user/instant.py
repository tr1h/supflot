import logging
from datetime import datetime, timedelta

from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.booking_service import BookingService
from services.payment_service import PaymentService
from services.notification_service import NotificationService
from keyboards.booking import main_menu_kb, confirm_kb

logger = logging.getLogger(__name__)
instant_router = Router()

class InstantStates(StatesGroup):
    select_board = State()
    select_duration = State()

@instant_router.message(F.text == "🏃 Арендовать сейчас")
async def book_now(message: types.Message, state: FSMContext):
    """Старт потока мгновенной аренды: показываем доступные доски"""
    await state.clear()
    avail = await BookingService.list_instant_boards(message.bot.db)
    if not avail:
        return await message.answer("❌ Нет доступных досок для мгновенной аренды.", reply_markup=main_menu_kb())
    kb = InlineKeyboardBuilder()
    for bid, name, price, free in avail:
        kb.button(text=f"{name} — {price}₽/ч (Своб. {free})", callback_data=f"inst_{bid}")
    kb.adjust(1)
    await message.answer("Выберите доску для мгновенной аренды:", reply_markup=kb.as_markup())
    await state.set_state(InstantStates.select_board)

@instant_router.callback_query(StateFilter(InstantStates.select_board), F.data.startswith("inst_"))
async def select_board(cq: types.CallbackQuery, state: FSMContext):
    """Выбор доски для мгновенной аренды: предлагаем длительности"""
    await cq.answer()
    bid = int(cq.data.split("_", 1)[1])
    board = await BookingService.get_board(cq.bot.db, bid)
    await state.update_data(
        board_id=bid,
        board_name=board['name'],
        price=board['price']
    )
    options = [30, 60, 120, 180]
    kb = InlineKeyboardBuilder()
    for m in options:
        label = f"{m} мин" if m < 60 else f"{m//60} ч"
        kb.button(text=label, callback_data=f"dur_{m}")
    kb.adjust(4)
    await cq.message.answer("На сколько минут?", reply_markup=kb.as_markup())
    await state.set_state(InstantStates.select_duration)

@instant_router.callback_query(StateFilter(InstantStates.select_duration), F.data.startswith("dur_"))
async def select_duration(cq: types.CallbackQuery, state: FSMContext):
    """Обработка длительности мгновенной аренды: рассчитываем время, сумму, записываем бронь"""
    await cq.answer()
    minutes = int(cq.data.split("_", 1)[1])
    data = await state.get_data()
    now = datetime.now()
    start_dt = (now + timedelta(minutes=5)).replace(second=0, microsecond=0)
    end_dt = start_dt + timedelta(minutes=minutes)
    amount = data['price'] * (minutes / 60)
    # записываем бронь со статусом active
    booking_id = await BookingService.create_instant_booking(
        db=cq.bot.db,
        user_id=cq.from_user.id,
        board_id=data['board_id'],
        date=start_dt.date().isoformat(),
        start_hour=start_dt.hour,
        start_minute=start_dt.minute,
        duration=minutes,
        quantity=1,
        amount=amount
    )
    text = (
        f"📝 Ваша мгновенная бронь оформлена:\n"
        f"🛶 {data['board_name']}\n"
        f"⏰ {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}\n"
        f"⏳ {minutes} мин | 💰 {amount:.2f} ₽"
    )
    await cq.message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())
    # уведомляем админов
    summary = BookingService.format_summary({
        'board_name': data['board_name'],
        'date': start_dt.date().isoformat(),
        'start': start_dt.hour,
        'start_minute': start_dt.minute,
        'duration': minutes,
        'quantity': 1,
        'amount': amount
    })
    await NotificationService.new_booking(cq.bot, booking_id, summary)
    # напоминание за 5 минут до
    NotificationService.schedule_reminder(
        user_id=cq.from_user.id,
        run_at=start_dt - timedelta(minutes=5),
        message=f"🔔 Напоминание: аренда {data['board_name']} начнётся в {start_dt.strftime('%H:%M')}"
    )
    # запрос отзыва после окончания
    NotificationService.schedule_reminder(
        user_id=cq.from_user.id,
        run_at=end_dt,
        message="🔔 Аренда окончена — оставьте, пожалуйста, отзыв: /review"
    )
    await state.clear()

__all__ = ["instant_router"]
