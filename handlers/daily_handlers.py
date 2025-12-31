# handlers/daily_handlers.py

import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import payment_choice_keyboard, user_main_menu as main_menu
from handlers.NEW_states import BookingState


logger = logging.getLogger(__name__)
daily_router = Router()

class DailyState(StatesGroup):
    select_board    = State()
    select_days     = State()
    choose_delivery = State()
    enter_address   = State()
    confirm         = State()

DAILY_RATE   = 1300
DELIVERY_FEE = 500

@daily_router.message(lambda m: m.text in {"📆 Суточная аренда", "Суточная аренда"})
async def cmd_daily(message: types.Message, state: FSMContext):
    await state.clear()
    rows = await message.bot.db.execute(
        "SELECT id,name FROM boards WHERE is_active=1", fetchall=True
    )
    if not rows:
        return await message.answer("❌ Нет доступных комплектов.", reply_markup=main_menu())
    kb = InlineKeyboardBuilder()
    for bid, nm in rows:
        kb.button(text=nm, callback_data=f"db_{bid}")
    kb.adjust(2)
    await message.answer("Выберите комплект (1300 ₽/день):", reply_markup=kb.as_markup())
    await state.set_state(DailyState.select_board)

@daily_router.callback_query(StateFilter(DailyState.select_board), F.data.startswith("db_"))
async def board_sel(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    bid = int(cq.data.split("_", 1)[1])
    nm  = (await cq.bot.db.execute(
        "SELECT name FROM boards WHERE id=?", (bid,), fetch="one"
    ))[0]
    await state.update_data(
        board_id=bid,
        board_name=nm,
        date=datetime.now().date().isoformat(),
        start_time=0,
        quantity=1,
    )
    kb = InlineKeyboardBuilder()
    for d in range(1, 8):
        kb.button(text=f"{d} дн", callback_data=f"dd_{d}")
    kb.adjust(4)
    await cq.message.answer("На сколько дней?", reply_markup=kb.as_markup())
    await state.set_state(DailyState.select_days)

@daily_router.callback_query(StateFilter(DailyState.select_days), F.data.startswith("dd_"))
async def days_sel(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    days = int(cq.data.split("_", 1)[1])
    amount = days * DAILY_RATE
    await state.update_data(days=days, amount=amount, duration=days * 24)
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🚚 Доставка +{DELIVERY_FEE}₽", callback_data="dv_yes")
    kb.button(text="🏄 Самовывоз", callback_data="dv_no")
    kb.adjust(2)
    await cq.message.answer(
        f"Стоимость без доставки: {amount} ₽\nНужна доставка?",
        reply_markup=kb.as_markup()
    )
    await state.set_state(DailyState.choose_delivery)

@daily_router.callback_query(StateFilter(DailyState.choose_delivery), F.data == "dv_yes")
async def deliv_yes(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    data = await state.get_data()
    total = data["amount"] + DELIVERY_FEE
    await state.update_data(amount=total)
    await cq.message.answer(f"Итого с доставкой: {total} ₽\nВведите адрес доставки:")
    await state.set_state(DailyState.enter_address)

@daily_router.callback_query(StateFilter(DailyState.choose_delivery), F.data == "dv_no")
async def deliv_no(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    data = await state.get_data()
    await cq.message.answer(f"Итого: {data['amount']} ₽")
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="dconfirm")
    kb.button(text="❌ Отменить", callback_data="dcancel")
    kb.adjust(2)
    await cq.message.answer("Перейти к оплате?", reply_markup=kb.as_markup())
    await state.set_state(DailyState.confirm)

@daily_router.message(StateFilter(DailyState.enter_address))
async def enter_address(msg: types.Message, state: FSMContext):
    address = msg.text.strip()
    await state.update_data(address=address)
    data = await state.get_data()
    total = data["amount"]
    await msg.answer(f"Адрес доставки: {address}\nИтого к оплате: {total} ₽")
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="dconfirm")
    kb.button(text="❌ Отменить", callback_data="dcancel")
    kb.adjust(2)
    await msg.answer("Перейти к оплате?", reply_markup=kb.as_markup())
    await state.set_state(DailyState.confirm)

@daily_router.callback_query(StateFilter(DailyState.confirm), F.data == "dconfirm")
async def daily_confirm(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    await cq.message.answer("Выберите способ оплаты:", reply_markup=payment_choice_keyboard())
    await state.set_state(BookingState.select_payment)

@daily_router.callback_query(StateFilter(DailyState.confirm), F.data == "dcancel")
async def daily_cancel(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer("Суточная аренда отменена.", show_alert=True)
    await cq.message.answer("Главное меню:", reply_markup=main_menu())
    await state.clear()
