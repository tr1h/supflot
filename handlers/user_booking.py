from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from core.database import Database

router = Router(name="user_booking")

class BookingFSM(StatesGroup):
    board_id = State()
    quantity = State()

def register_user_booking(dp: Router, db: Database):
    dp.include_router(router)

    @router.message(F.text.startswith("/book_"))
    async def start_booking(msg: types.Message, state: FSMContext):
        try:
            board_id = int(msg.text.split("_")[1])
            board = await db.execute("SELECT name, quantity FROM boards WHERE id = ?", (board_id,), fetch=True)
            if not board:
                return await msg.answer("❌ Доска не найдена.")
            name, available = board
            await state.update_data(board_id=board_id)
            await state.set_state(BookingFSM.quantity)
            await msg.answer(f"Вы выбрали доску «{name}». Доступно: {available} шт.\nВведите количество для брони:")
        except Exception:
            await msg.answer("⚠️ Неверная команда.")

    @router.message(BookingFSM.quantity)
    async def finish_booking(msg: types.Message, state: FSMContext):
        try:
            qty = int(msg.text)
            if qty <= 0:
                raise ValueError
        except ValueError:
            return await msg.answer("❌ Введите положительное число.")

        data = await state.get_data()
        board_id = data["board_id"]

        available = await db.execute("SELECT quantity FROM boards WHERE id = ?", (board_id,), fetch=True)
        if not available or available[0] < qty:
            return await msg.answer("❗ Недостаточно досок в наличии.")

        await db.execute("UPDATE boards SET quantity = quantity - ? WHERE id = ?", (qty, board_id), commit=True)
        await db.execute(
            """INSERT INTO bookings (user_id, board_id, quantity, start_time)
               VALUES (?, ?, ?, datetime('now'))""",
            (msg.from_user.id, board_id, qty), commit=True
        )

        await state.clear()
        await msg.answer(f"✅ Бронирование оформлено на {qty} шт.")
