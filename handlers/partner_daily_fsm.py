# handlers/partner_daily_fsm.py
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.database import Database

router = Router(name="partner_daily_fsm")

class DailyFSM(StatesGroup):
    choosing_board = State()
    entering_price = State()
    entering_quantity = State()
    entering_pickup_note = State()
    entering_delivery_note = State()

def register_partner_daily_fsm(dp: Router, db: Database):
    dp.include_router(router)

    @router.callback_query(F.data == "add_daily_board")
    async def choose_board(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        partner_id = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute("SELECT id, name FROM boards WHERE partner_id=?", (partner_id,), fetchall=True)
        if not rows:
            return await cq.message.answer("❌ У вас нет досок.")

        kb = InlineKeyboardBuilder()
        for bid, name in rows:
            kb.button(text=name, callback_data=f"daily_b_{bid}")
        kb.adjust(1)
        await cq.message.answer("Выберите доску для суточной аренды:", reply_markup=kb.as_markup())
        await state.set_state(DailyFSM.choosing_board)

    @router.callback_query(DailyFSM.choosing_board, F.data.startswith("daily_b_"))
    async def set_price(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        board_id = int(cq.data.split("_")[2])
        await state.update_data(board_id=board_id)
        await cq.message.answer("Введите цену за сутки:")
        await state.set_state(DailyFSM.entering_price)

    @router.message(DailyFSM.entering_price)
    async def set_quantity(msg: types.Message, state: FSMContext):
        try:
            price = float(msg.text.replace(",", "."))
            if price <= 0:
                raise ValueError
        except ValueError:
            return await msg.answer("❌ Введите корректную цену.")
        await state.update_data(daily_price=price)
        await msg.answer("Введите доступное количество досок:")
        await state.set_state(DailyFSM.entering_quantity)

    @router.message(DailyFSM.entering_quantity)
    async def set_pickup_note(msg: types.Message, state: FSMContext):
        try:
            qty = int(msg.text)
            if qty <= 0:
                raise ValueError
        except ValueError:
            return await msg.answer("❌ Введите положительное число.")
        await state.update_data(available_quantity=qty)
        await msg.answer("Опишите условия самовывоза (например: «м. Савёловская, с 10 до 21»):")
        await state.set_state(DailyFSM.entering_pickup_note)

    @router.message(DailyFSM.entering_pickup_note)
    async def set_delivery_note(msg: types.Message, state: FSMContext):
        await state.update_data(pickup_note=msg.text.strip())
        await msg.answer("Условия доставки (или - если недоступно):")
        await state.set_state(DailyFSM.entering_delivery_note)

    @router.message(DailyFSM.entering_delivery_note)
    async def save_daily_board(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        await db.execute(
            "INSERT INTO daily_boards (board_id, daily_price, available_quantity, pickup_note, delivery_note) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                data["board_id"],
                data["daily_price"],
                data["available_quantity"],
                data["pickup_note"],
                msg.text.strip()
            ),
            commit=True
        )
        await msg.answer("✅ Доска добавлена в суточную аренду!")
        await state.clear()
