# handlers/user_cabinet.py
# -*- coding: utf-8 -*-
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

user_cabinet_router = Router()

def register_user_cabinet(router: Router, db):
    @router.message(F.text == "👤 Мой кабинет")
    async def my_cabinet_handler(msg: types.Message):
        await show_client_cabinet(msg, db)

    @router.callback_query(F.data == "cab_active")
    async def show_active_bookings(cq: types.CallbackQuery):
        await cq.answer()
        user_id = cq.from_user.id
        rows = await db.execute(
            """
            SELECT b.name, bk.date, bk.start_time, bk.duration
              FROM bookings bk
              JOIN boards b ON bk.board_id = b.id
             WHERE bk.user_id = ?
               AND bk.status IN ('active','waiting_card','waiting_cash')
             ORDER BY bk.date DESC
            """,
            (user_id,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("🕊️ У вас нет активных броней.")
        text = "🟢 <b>Активные брони:</b>\n\n"
        for name, date, hour, dur in rows:
            text += f"• {name} — {date} {hour:02}:00 ({dur} ч)\n"
        await cq.message.answer(text, parse_mode="HTML")

    @router.callback_query(F.data == "cab_history")
    async def show_booking_history(cq: types.CallbackQuery):
        await cq.answer()
        user_id = cq.from_user.id
        rows = await db.execute(
            """
            SELECT b.name, bk.date, bk.start_time, bk.duration, bk.amount
              FROM bookings bk
              JOIN boards b ON bk.board_id = b.id
             WHERE bk.user_id = ?
             ORDER BY bk.id DESC
             LIMIT 5
            """,
            (user_id,), fetchall=True
        )
        if not rows:
            return await cq.message.answer("📭 История пуста.")
        text = "📜 <b>Последние брони:</b>\n\n"
        for name, date, hour, dur, amt in rows:
            text += f"• {name} — {date} {hour:02}:00 ({dur} ч), {amt:.0f}₽\n"
        await cq.message.answer(text, parse_mode="HTML")

    @router.callback_query(F.data == "cab_apply_partner")
    async def apply_for_partner(cq: types.CallbackQuery):
        await cq.answer()
        user_id = cq.from_user.id

        # есть ли он уже в таблице partners?
        row = await db.execute(
            "SELECT id, is_approved FROM partners WHERE telegram_id = ?",
            (user_id,), fetch=True
        )
        if row:
            if row[1]:  # is_approved == 1
                return await cq.message.answer("✅ Вы уже являетесь партнёром.")
            else:
                return await cq.message.answer("⏳ Ваша заявка уже на рассмотрении.")
        # создаём чернового партнёра
        await db.execute(
            "INSERT INTO partners (name, telegram_id, is_approved) VALUES (?, ?, 0)",
            (cq.from_user.full_name or "Партнёр", user_id),
            commit=True
        )
        await cq.message.answer("✅ Заявка на партнёрство отправлена! Мы свяжемся с вами.")

async def show_client_cabinet(msg: types.Message, db):
    user_id = msg.from_user.id

    # статистика бронирований
    row = await db.execute(
        "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM bookings WHERE user_id = ?",
        (user_id,), fetch=True
    )
    total, spent = row or (0, 0)

    # проверяем статус партнёра
    partner_row = await db.execute(
        "SELECT is_approved FROM partners WHERE telegram_id = ?",
        (user_id,), fetch=True
    )
    is_partner = bool(partner_row)  # есть запись
    is_approved = bool(partner_row[0]) if partner_row else False

    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Активные", callback_data="cab_active")
    kb.button(text="📜 История", callback_data="cab_history")

    if not is_partner:
        kb.button(text="📩 Подать заявку на партнёрство", callback_data="cab_apply_partner")
    elif is_partner and is_approved:
        kb.button(text="👥 Партнёрский кабинет", callback_data="cab_as_partner")
    else:
        kb.button(text="⏳ Заявка рассматривается", callback_data="noop_pending")

    kb.adjust(2, 1)

    text = (
        f"{hbold('👤 Личный кабинет')}\n\n"
        f"{hbold('🔢 Всего броней:')} {total}\n"
        f"{hbold('💰 Потрачено:')} {spent:.2f} ₽\n\n"
        "Выберите действие:"
    )
    await msg.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
