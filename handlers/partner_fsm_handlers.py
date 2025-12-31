# handlers/partner_fsm_handlers.py
# -*- coding: utf-8 -*-
from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from keyboards.common import main_menu
import logging

class PartnerApplyFSM(StatesGroup):
    name = State()
    email = State()

class AddDailyBoardFSM(StatesGroup):
    name = State()
    price = State()
    address = State()

partner_fsm_router = Router()

def register_partner_fsm_handlers(dp: Router, db):
    dp.include_router(partner_fsm_router)

    # ─── Подача заявки на партнёрство ──────────────────────
    @partner_fsm_router.message(F.text == "/partner")
    async def start_application(msg: types.Message, state: FSMContext):
        user_id = msg.from_user.id
        row = await db.execute(
            "SELECT id, is_approved FROM partners WHERE telegram_id = ?",
            (user_id,), fetch="one"
        )
        if row:
            if row[1]:
                return await msg.answer("✅ Вы уже партнёр.")
            return await msg.answer("⏳ Заявка уже на рассмотрении.")
        await msg.answer("Введите название вашего проката/имя:")
        await state.set_state(PartnerApplyFSM.name)

    @partner_fsm_router.message(PartnerApplyFSM.name)
    async def partner_set_name(msg: types.Message, state: FSMContext):
        await state.update_data(name=msg.text.strip())
        await msg.answer("Укажите контактный email (или отправьте «-»):")
        await state.set_state(PartnerApplyFSM.email)

    @partner_fsm_router.message(PartnerApplyFSM.email)
    async def partner_finish_apply(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        name = data.get("name")
        email = msg.text.strip()
        if email == "-":
            email = None

        # Сохраняем нового партнёра
        try:
            await db.execute(
                """
                INSERT INTO partners (name, contact_email, telegram_id, is_approved)
                VALUES (?, ?, ?, 0)
                """,
                (name, email, msg.from_user.id),
                commit=True
            )
            result = await db.execute("SELECT last_insert_rowid()", fetch="one")
            partner_id = result[0]
            logging.info(f"[PARTNER CREATED] ID: {partner_id}, telegram_id: {msg.from_user.id}")
            await msg.answer("✅ Заявка отправлена! Мы свяжемся с вами.")
        except Exception as e:
            logging.exception("Ошибка при регистрации партнёра")
            await msg.answer("❌ Ошибка при регистрации. Попробуйте позже.")

        await state.clear()

    @partner_fsm_router.callback_query(F.data == "noop_pending")
    async def noop_pending(cq: types.CallbackQuery):
        await cq.answer("Заявка на партнёрство рассматривается", show_alert=True)

    # ─── FSM: Сдать доску в суточную аренду ─────────────────
    @partner_fsm_router.callback_query(F.data == "add_daily_board")
    async def start_add_daily_board(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.clear()
        await cq.message.answer("📝 Введите название доски:")
        await state.set_state(AddDailyBoardFSM.name)

    @partner_fsm_router.message(AddDailyBoardFSM.name)
    async def set_daily_board_name(msg: types.Message, state: FSMContext):
        await state.update_data(name=msg.text.strip())
        await msg.answer("💰 Укажите цену за сутки:")
        await state.set_state(AddDailyBoardFSM.price)

    @partner_fsm_router.message(AddDailyBoardFSM.price)
    async def set_daily_board_price(msg: types.Message, state: FSMContext):
        try:
            price = float(msg.text.replace(",", "."))
            if price <= 0:
                raise ValueError
        except ValueError:
            return await msg.answer("❗ Укажите корректную цену (например, 1500).")
        await state.update_data(price=price)
        await msg.answer("📍 Укажите адрес (или способ выдачи):")
        await state.set_state(AddDailyBoardFSM.address)

    @partner_fsm_router.message(AddDailyBoardFSM.address)
    async def finish_daily_board(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        user_id = msg.from_user.id

        await db.execute(
            """
            INSERT INTO daily_boards (name, daily_price, address, partner_id, is_active, available_quantity)
            VALUES (?, ?, ?, (SELECT id FROM partners WHERE telegram_id = ?), 1, 1)
            """,
            (data["name"], data["price"], msg.text.strip(), user_id),
            commit=True
        )
        await state.clear()
        await msg.answer("✅ Доска добавлена и доступна для аренды!", reply_markup=main_menu())
