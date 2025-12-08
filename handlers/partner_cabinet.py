# handlers/partner_cabinet.py
# -*- coding: utf-8 -*-
import io
import logging

from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from helpers.wallet import get_employee_balance
from core.database import Database
from helpers.wallet import get_partner_balance, get_employee_balance
from handlers.partner_fsm_handlers import AddDailyBoardFSM, partner_fsm_router

logger = logging.getLogger(__name__)
router = Router(name="partner_cabinet")


# ─── FSM: состояния ─────────────────────────────────────────────────────────
class AddLocationFSM(StatesGroup):
    name = State()

class AddBoardFSM(StatesGroup):
    location_id = State()
    board_name  = State()
    price       = State()
    quantity    = State()

class EditBoardFSM(StatesGroup):
    choose    = State()
    new_value = State()

class WithdrawFSM(StatesGroup):
    amount = State()

class AddEmployeeFSM(StatesGroup):
    telegram_id = State()
    percent     = State()


# ─── Главное меню партнёра ───────────────────────────────────────────────────
async def show_partner_cabinet(msg: types.Message, db: Database):
    kb = InlineKeyboardBuilder()
    kb.button(text="⏳ Ожидающие брони",        callback_data="partner_pending")
    kb.button(text="📦 Оформленные заказы",      callback_data="partner_orders")
    kb.button(text="📍 Добавить локацию",        callback_data="partner_add_location")
    kb.button(text="🏄 Добавить доску",          callback_data="partner_add_board")
    kb.button(text="📌 Мои локации",             callback_data="partner_my_locations")
    kb.button(text="📆 Сдать в суточную аренду", callback_data="add_daily_board")
    kb.button(text="📋 Мои доски",              callback_data="partner_my_boards")
    kb.button(text="✏️ Редактировать доски",     callback_data="partner_edit_boards")
    kb.button(text="📈 График дохода",           callback_data="partner_income_graph")
    kb.button(text="📊 Доход",                   callback_data="partner_income")
    kb.button(text="💼 Кошелёк",                 callback_data="partner_wallet")
    kb.button(text="💳 Запросить выплату",       callback_data="partner_withdraw")
    kb.button(text="📜 История заявок",          callback_data="partner_withdraw_history")
    kb.button(text="👥 Добавить сотрудника",     callback_data="partner_add_employee")
    kb.button(text="👥 Мои сотрудники",          callback_data="partner_my_employees")
    kb.button(text="🔙 Назад",                   callback_data="back_to_partner")
    kb.adjust(2)

    await msg.answer(
        hbold("👥 Партнёрский кабинет") + "\n\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    bal = await get_partner_balance(db, msg.from_user.id)
    await msg.answer(f"💳 Баланс кошелька: {bal:.2f} ₽")


# ─── Кабинет сотрудника ─────────────────────────────────────────────────────
async def show_employee_cabinet(msg: types.Message, db: Database):
    row = await db.execute(
        "SELECT partner_id FROM employees WHERE telegram_id = ?",
        (str(msg.from_user.id),), fetch="one"
    )
    if not row:
        return await msg.answer("❌ Вы не зарегистрированы как сотрудник.")
    # покажем доход от комиссий
    emp_bal = await get_employee_balance(db, msg.from_user.id)
    await msg.answer(f"💰 Ваш доход (комиссия): {emp_bal:.2f} ₽")

    kb = InlineKeyboardBuilder()
    kb.button(text="⏳ Ожидающие брони",        callback_data="employee_pending")
    kb.button(text="📦 Оформленные заказы",      callback_data="employee_orders")
    kb.button(text="📋 Мои доски",               callback_data="employee_my_boards")
    kb.button(text="📌 Локации партнёра",        callback_data="employee_my_locations")
    kb.button(text="📈 График дохода",           callback_data="employee_income_graph")
    kb.button(text="📊 Доход",                   callback_data="employee_income")
    kb.button(text="🔙 Назад",                   callback_data="back_to_partner")
    kb.adjust(2)

    await msg.answer(
        hbold("👤 Кабинет сотрудника") + "\n\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


# ─── Регистрация роутера ────────────────────────────────────────────────────
def register_partner_cabinet(dp: Router, db: Database):
    dp.include_router(router)

    # 1) Открыть партнёрский кабинет по кнопке
    @router.callback_query(F.data == "cab_as_partner")
    async def _cab(cq: types.CallbackQuery):
        await cq.answer()
        await show_partner_cabinet(cq.message, db)

    # 2) Открыть кабинет сотрудника по команде /employee
    @router.message(F.text == "/employee")
    async def _cmd_employee(msg: types.Message):
        await show_employee_cabinet(msg, db)


    # ── Ожидающие брони ────────────────────────────────────────────────────
    @router.callback_query(F.data == "partner_pending")
    async def _show_pending(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            """
            SELECT bk.id, u.full_name, b.name, bk.date,
                   bk.start_time, bk.duration, bk.amount, bk.status
            FROM bookings bk
            JOIN boards b ON bk.board_id = b.id
            JOIN users u  ON bk.user_id  = u.id
            WHERE b.partner_id = ?
              AND bk.status IN ('waiting_partner','waiting_card','waiting_cash')
            ORDER BY bk.created_at DESC
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("⏳ Ожидающих брони нет.")
        for oid, user, nm, d, h, dur, amt, status in rows:
            verb = ("подтвердить" if status == 'waiting_partner' else "забрать оплату")
            txt = (
                f"#{oid} {user} — «{nm}»\n"
                f"📅 {d} в {h}:00 на {dur}ч — {amt:.0f}₽ ({status})\n\n"
                f"Что делаем? ({verb})"
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Подтвердить", callback_data=f"confirm_booking_{oid}")
            kb.button(text="❌ Отменить",    callback_data=f"cancel_booking_{oid}")
            kb.adjust(2)
            await cq.message.answer(txt, reply_markup=kb.as_markup())


    @router.callback_query(F.data == "employee_pending")
    async def _show_pending_emp(cq: types.CallbackQuery):
        await cq.answer()
        row = await db.execute(
            "SELECT partner_id FROM employees WHERE telegram_id = ?",
            (str(cq.from_user.id),), fetch="one"
        )
        if not row:
            return await cq.message.answer("❌ Вы не сотрудник.")
        pid = row[0]
        rows = await db.execute(
            """
            SELECT bk.id, u.full_name, b.name, bk.date,
                   bk.start_time, bk.duration, bk.amount, bk.status
            FROM bookings bk
            JOIN boards b ON bk.board_id = b.id
            JOIN users u  ON bk.user_id  = u.id
            WHERE b.partner_id = ?
              AND bk.status IN ('waiting_partner','waiting_card','waiting_cash')
            ORDER BY bk.created_at DESC
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("⏳ Ожидающих брони нет.")
        for oid, user, nm, d, h, dur, amt, status in rows:
            verb = ("подтвердить" if status == 'waiting_partner' else "забрать оплату")
            txt = (
                f"#{oid} {user} — «{nm}»\n"
                f"📅 {d} в {h}:00 на {dur}ч — {amt:.0f}₽ ({status})\n\n"
                f"Что делаем? ({verb})"
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Подтвердить", callback_data=f"confirm_booking_{oid}")
            kb.button(text="❌ Отменить",    callback_data=f"cancel_booking_{oid}")
            kb.adjust(2)
            await cq.message.answer(txt, reply_markup=kb.as_markup())


    # ── Подтвердить / Отменить бронь ─────────────────────────────────────────
    @router.callback_query(F.data.startswith("confirm_booking_"))
    async def _confirm_booking(cq: types.CallbackQuery):
        oid = int(cq.data.split("_")[-1])
        await cq.answer()
        await db.execute(
            "UPDATE bookings SET status='active' WHERE id=? "
            "AND status IN ('waiting_partner','waiting_card','waiting_cash')",
            (oid,), commit=True
        )
        await cq.message.answer(f"✅ Бронь #{oid} подтверждена.")

    @router.callback_query(F.data.startswith("cancel_booking_"))
    async def _cancel_booking(cq: types.CallbackQuery):
        oid = int(cq.data.split("_")[-1])
        await cq.answer()
        await db.execute(
            "UPDATE bookings SET status='canceled' WHERE id=? "
            "AND status IN ('waiting_partner','waiting_card','waiting_cash')",
            (oid,), commit=True
        )
        await cq.message.answer(f"❌ Бронь #{oid} отменена.")
        # оповестить пользователя
        row = await db.execute(
            "SELECT user_id FROM bookings WHERE id = ?", (oid,), fetch="one"
        )
        if row:
            await cq.bot.send_message(row[0], f"❌ Ваша бронь #{oid} отменена партнёром.")


    # ── Оформленные заказы ─────────────────────────────────────────────────
    @router.callback_query(F.data == "partner_orders")
    async def _show_orders(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            """
            SELECT bk.id, u.full_name, b.name, bk.date,
                   bk.start_time, bk.duration, bk.amount, bk.status
            FROM bookings bk
            JOIN boards b ON bk.board_id = b.id
            JOIN users u  ON bk.user_id  = u.id
            WHERE b.partner_id = ?
            ORDER BY bk.created_at DESC
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("📦 Нет заказов.")
        text = "📦 <b>Заказы:</b>\n\n"
        for oid, user, nm, d, h, dur, amt, st in rows:
            text += (
                f"#{oid} {user} — «{nm}»\n"
                f"  📅 {d} в {h}:00 на {dur}ч — {amt:.0f}₽ ({st})\n\n"
            )
        await cq.message.answer(text, parse_mode="HTML")


    @router.callback_query(F.data == "employee_orders")
    async def _emp_orders(cq: types.CallbackQuery):
        await cq.answer()
        row = await db.execute(
            "SELECT partner_id FROM employees WHERE telegram_id = ?",
            (str(cq.from_user.id),), fetch="one"
        )
        if not row:
            return await cq.message.answer("❌ Вы не сотрудник.")
        pid = row[0]
        rows = await db.execute(
            """
            SELECT bk.id, u.full_name, b.name, bk.date,
                   bk.start_time, bk.duration, bk.amount, bk.status
            FROM bookings bk
            JOIN boards b ON bk.board_id = b.id
            JOIN users u  ON bk.user_id  = u.id
            WHERE b.partner_id = ?
            ORDER BY bk.created_at DESC
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("📦 Нет заказов.")
        for oid, user, nm, d, h, dur, amt, st in rows:
            await cq.message.answer(
                f"#{oid} {user} — «{nm}» — {amt:.0f}₽ — {st}"
            )


    # ── Суточная аренда через FSM партнёра ─────────────────────────────────────
    @router.callback_query(F.data == "add_daily_board")
    async def _daily(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        # передаём управление в partner_fsm_handlers
        await partner_fsm_router.dispatch(cq, state=state)


    # ── Добавление/редактирование локаций и досок ─────────────────────────────
    @router.callback_query(F.data == "partner_add_location")
    async def _add_loc_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.set_state(AddLocationFSM.name)
        await cq.message.answer("Введите название новой локации:")

    @router.message(AddLocationFSM.name)
    async def _add_loc_finish(msg: types.Message, state: FSMContext):
        name = msg.text.strip()
        if not name:
            return await msg.answer("❌ Название не может быть пустым.")
        pid = await db.get_partner_id_by_telegram(msg.from_user.id)
        await db.execute(
            "INSERT INTO locations(partner_id,name,is_active) VALUES(?,?,1)",
            (pid, name), commit=True
        )
        await msg.answer(f"✅ Локация «{name}» добавлена.")
        await state.clear()
        await show_partner_cabinet(msg, db)

    @router.callback_query(F.data == "partner_my_locations")
    async def _my_locs(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            "SELECT name FROM locations WHERE partner_id = ?", (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("❌ Локаций нет.")
        text = "📌 <b>Локации:</b>\n" + "\n".join(f"• {n}" for (n,) in rows)
        await cq.message.answer(text, parse_mode="HTML")


    @router.callback_query(F.data == "partner_add_board")
    async def _add_board_start(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            "SELECT id,name FROM locations WHERE partner_id = ? AND is_active = 1",
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("❗ Сначала добавьте локацию.")
        kb = InlineKeyboardBuilder()
        for lid, lname in rows:
            kb.button(text=lname, callback_data=f"select_location_{lid}")
        kb.adjust(1)
        await cq.message.answer("Выберите локацию:", reply_markup=kb.as_markup())

    @router.callback_query(F.data.startswith("select_location_"))
    async def _board_loc_selected(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        lid = int(cq.data.split("_")[-1])
        await state.update_data(location_id=lid)
        await state.set_state(AddBoardFSM.board_name)
        await cq.message.answer("Введите название доски:")

    @router.message(AddBoardFSM.board_name)
    async def _board_name(msg: types.Message, state: FSMContext):
        await state.update_data(board_name=msg.text.strip())
        await state.set_state(AddBoardFSM.price)
        await msg.answer("💰 Цена аренды (число):")

    @router.message(AddBoardFSM.price)
    async def _board_price(msg: types.Message, state: FSMContext):
        try:
            p = float(msg.text.replace(",","."))
            if p <= 0: raise ValueError
        except:
            return await msg.answer("❌ Некорректная цена.")
        await state.update_data(price=p)
        await state.set_state(AddBoardFSM.quantity)
        await msg.answer("🔢 Количество доск:")

    @router.message(AddBoardFSM.quantity)
    async def _board_qty(msg: types.Message, state: FSMContext):
        try:
            q = int(msg.text)
            if q <= 0: raise ValueError
        except:
            return await msg.answer("❌ Введите целое число > 0.")
        data = await state.get_data()
        pid = await db.get_partner_id_by_telegram(msg.from_user.id)
        await db.execute(
            """
            INSERT INTO boards(partner_id,location_id,name,price,total,quantity)
            VALUES(?,?,?,?,?,?)
            """,
            (pid, data["location_id"], data["board_name"],
             data["price"], q, q),
            commit=True
        )
        await msg.answer("✅ Доска добавлена.")
        await state.clear()
        await show_partner_cabinet(msg, db)


    @router.callback_query(F.data == "partner_my_boards")
    async def _my_boards(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            """
            SELECT b.name, l.name, b.price, b.quantity, b.total
            FROM boards b
            JOIN locations l ON b.location_id = l.id
            WHERE b.partner_id = ?
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("❌ Досок нет.")
        text = "📋 <b>Доски:</b>\n"
        for nm, loc, pr, q, tot in rows:
            text += f"• {nm} @ «{loc}» — {pr:.0f}₽ × {q}/{tot}\n"
        await cq.message.answer(text, parse_mode="HTML")


    @router.callback_query(F.data == "partner_edit_boards")
    async def _edit_boards(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            "SELECT id,name FROM boards WHERE partner_id = ?", (pid,), fetchall=True
        )
        kb = InlineKeyboardBuilder()
        for bid, nm in rows:
            kb.button(text=nm, callback_data=f"edit_choose_{bid}")
        kb.adjust(1)
        await cq.message.answer("Выберите доску:", reply_markup=kb.as_markup())

    @router.callback_query(F.data.startswith("edit_choose_"))
    async def _edit_choose(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split("_")[-1])
        await state.update_data(bid=bid)
        await state.set_state(EditBoardFSM.choose)
        kb = InlineKeyboardBuilder()
        kb.button(text="Цена",   callback_data="edit_price")
        kb.button(text="Кол-во", callback_data="edit_qty")
        kb.adjust(2)
        await cq.message.answer("Что редактируем?", reply_markup=kb.as_markup())

    @router.callback_query(StateFilter(EditBoardFSM.choose), F.data.in_(["edit_price","edit_qty"]))
    async def _edit_field(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        which = cq.data.split("_")[1]
        await state.update_data(which=which)
        await state.set_state(EditBoardFSM.new_value)
        await cq.message.answer("Введите новое значение:")

    @router.message(StateFilter(EditBoardFSM.new_value))
    async def _apply_edit(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        field = "price" if data["which"] == "price" else "quantity"
        try:
            val = float(msg.text) if field=="price" else int(msg.text)
        except:
            return await msg.answer("❌ Неверный формат.")
        await db.execute(
            f"UPDATE boards SET {field} = ? WHERE id = ?",
            (val, data["bid"]), commit=True
        )
        await msg.answer("✅ Обновлено.")
        await state.clear()
        await show_partner_cabinet(msg, db)


    # ── Доход и график ────────────────────────────────────────────────────────
    @router.callback_query(F.data == "partner_income")
    async def _income(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        row = await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM partner_wallet_ops WHERE partner_id = ? AND type='credit'",
            (pid,), fetch="one"
        )
        await cq.message.answer(f"📊 Доход: {row[0]:.2f} ₽")

    @router.callback_query(F.data == "partner_income_graph")
    async def _income_graph(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.execute(  # use telegram → partner_id
            "SELECT id FROM partners WHERE telegram_id = ?",
            (cq.from_user.id,), fetch="one"
        )
        pid = pid[0]
        rows = await db.execute(
            """
            SELECT date(created_at), SUM(amount)
            FROM partner_wallet_ops
            WHERE partner_id = ? AND type='credit'
            GROUP BY date(created_at)
            ORDER BY date(created_at)
            """,
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("📉 Нет данных.")
        dates, vals = zip(*rows)
        buf = io.BytesIO()
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6,3))
        plt.plot(dates, vals, marker="o")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        await cq.bot.send_photo(cq.from_user.id, buf, caption="📈 Доход")


    # ── Кошелёк и выплаты ──────────────────────────────────────────────────────
    @router.callback_query(F.data == "partner_wallet")
    async def _wallet(cq: types.CallbackQuery):
        await cq.answer()
        bal = await get_partner_balance(db, cq.from_user.id)
        await cq.message.answer(f"💼 Баланс кошелька: {bal:.2f} ₽")


    @router.callback_query(F.data == "partner_withdraw")
    async def _withdraw_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        bal = await get_partner_balance(db, cq.from_user.id)
        if bal < 500:
            await cq.message.answer(f"❌ Мин. сумма — 500 ₽ (баланс: {bal:.2f} ₽)")
            return await show_partner_cabinet(cq.message, db)
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        recent = await db.execute(
            "SELECT 1 FROM partner_withdraw_requests "
            "WHERE partner_id = ? AND status='pending' "
            "AND created_at >= datetime('now','-1 day')",
            (pid,), fetch="one"
        )
        if recent:
            await cq.message.answer("⏳ Уже подавали заявку за 24 ч.")
            return await show_partner_cabinet(cq.message, db)
        await state.set_state(WithdrawFSM.amount)
        await cq.message.answer(f"💰 Баланс: {bal:.2f} ₽\nВведите сумму для вывода:")

    @router.message(WithdrawFSM.amount)
    async def _withdraw_confirm(msg: types.Message, state: FSMContext):
        try:
            amt = float(msg.text.replace(",","."))
            if amt <= 0: raise ValueError
        except:
            return await msg.answer("❗ Введите корректную сумму.")
        pid = await db.get_partner_id_by_telegram(msg.from_user.id)
        bal = await get_partner_balance(db, msg.from_user.id)
        if amt > bal:
            await state.clear()
            await msg.answer(f"❌ Недостаточно средств ({bal:.2f} ₽).")
            return await show_partner_cabinet(msg, db)
        await db.execute(
            "INSERT INTO partner_withdraw_requests(partner_id,amount,status) "
            "VALUES(?,?, 'pending')",
            (pid, amt), commit=True
        )
        await msg.answer(f"✅ Заявка на {amt:.2f} ₽ создана.")
        await state.clear()
        await show_partner_cabinet(msg, db)

    @router.callback_query(F.data == "partner_withdraw_history")
    async def _withdraw_history(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            "SELECT amount,status,created_at FROM partner_withdraw_requests "
            "WHERE partner_id = ? ORDER BY created_at DESC LIMIT 10",
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("📭 Нет заявок.")
        emojis = {"pending":"⏳","approved":"✅","rejected":"❌"}
        text = "📜 <b>История заявок:</b>\n\n"
        for amt, st, dt in rows:
            text += f"{emojis.get(st,'❔')} {amt:.2f} ₽ — {st.upper()} ({dt})\n"
        await cq.message.answer(text, parse_mode="HTML")


    # ─── Управление сотрудниками ─────────────────────────────────────────────
    @router.callback_query(F.data == "partner_add_employee")
    async def _add_employee_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.set_state(AddEmployeeFSM.telegram_id)
        await cq.message.answer("Введите Telegram ID или @username сотрудника:")

    @router.message(AddEmployeeFSM.telegram_id)
    async def _add_employee_id(msg: types.Message, state: FSMContext):
        tid = msg.text.strip().lstrip("@")
        await state.update_data(telegram_id=tid)
        await state.set_state(AddEmployeeFSM.percent)
        await msg.answer("Укажите процент от продаж (0–100):")

    @router.message(AddEmployeeFSM.percent)
    async def _add_employee_percent(msg: types.Message, state: FSMContext):
        try:
            pct = float(msg.text.replace(",","."))
            if not (0 <= pct <= 100):
                raise ValueError
        except:
            return await msg.answer("❌ Некорректный процент, введите 0–100.")
        data = await state.get_data()
        pid = await db.get_partner_id_by_telegram(msg.from_user.id)
        exists = await db.execute(
            "SELECT 1 FROM employees WHERE telegram_id = ? AND partner_id = ?",
            (data["telegram_id"], pid), fetch="one"
        )
        if exists:
            await msg.answer(f"❗ Сотрудник @{data['telegram_id']} уже есть.")
        else:
            await db.execute(
                "INSERT INTO employees(telegram_id,partner_id,commission_percent) "
                "VALUES(?,?,?)",
                (data["telegram_id"], pid, pct), commit=True
            )
            await msg.answer(f"✅ @{data['telegram_id']} добавлен, комиссия {pct:.1f}%.")
        await state.clear()
        await show_partner_cabinet(msg, db)

    @router.callback_query(F.data == "partner_my_employees")
    async def _list_employees(cq: types.CallbackQuery):
        await cq.answer()
        pid = await db.get_partner_id_by_telegram(cq.from_user.id)
        rows = await db.execute(
            "SELECT telegram_id,commission_percent FROM employees WHERE partner_id = ?",
            (pid,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("👥 Сотрудников нет.")
        text = "👥 <b>Сотрудники:</b>\n\n" + "\n".join(
            f"• @{tid} — {pct:.1f}%" for tid, pct in rows
        )
        await cq.message.answer(text, parse_mode="HTML")


    # ─── Назад в главное меню ────────────────────────────────────────────────
    @router.callback_query(F.data == "back_to_partner")
    async def _back(cq: types.CallbackQuery):
        await cq.answer()
        await show_partner_cabinet(cq.message, db)


__all__ = ["register_partner_cabinet", "show_partner_cabinet"]
