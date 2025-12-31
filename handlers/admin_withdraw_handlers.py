# handlers/admin_withdraw_handlers.py
# -*- coding: utf-8 -*-
"""
Админские хендлеры для просмотра и обработки заявок партнёров на вывод средств.
"""

import logging
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database import Database
from helpers.wallet import get_partner_balance
from keyboards.new_admin_menu import BTN_WITHDRAWALS

admin_withdraw_router = Router()
db: Database = None

def register_admin_withdraw(dp: Router, database: Database):
    global db
    db = database
    dp.include_router(admin_withdraw_router)

# ─── 1) Список заявок на вывод ───
@admin_withdraw_router.message(F.text == BTN_WITHDRAWALS)
async def list_withdraw_requests(msg: types.Message):
    rows = await db.execute(
        """
        SELECT wr.id, wr.partner_id, wr.amount, wr.created_at
          FROM partner_withdraw_requests AS wr
         WHERE wr.status = 'pending'
         ORDER BY wr.created_at
        """,
        fetchall=True
    )

    if not rows:
        return await msg.answer("📭 Нет заявок на вывод.")

    for req_id, partner_id, amount, created in rows:
        text = (
            f"💸 <b>Заявка #{req_id}</b>\n"
            f"Сумма: <b>{amount:.2f} ₽</b>\n"
            f"Дата: {created}"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Одобрить", callback_data=f"withdraw_approve:{req_id}")
        kb.button(text="❌ Отклонить", callback_data=f"withdraw_reject:{req_id}")
        kb.adjust(2)
        await msg.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

# ─── 2) Одобрение заявки ───
@admin_withdraw_router.callback_query(F.data.startswith("withdraw_approve:"))
async def admin_approve(cq: types.CallbackQuery):
    await cq.answer()
    req_id = int(cq.data.split(":")[1])

    row = await db.execute(
        """
        SELECT wr.partner_id, wr.amount, p.telegram_id
          FROM partner_withdraw_requests AS wr
     LEFT JOIN partners AS p ON p.id = wr.partner_id
         WHERE wr.id = ? AND wr.status = 'pending'
        """,
        (req_id,), fetch="one"
    )
    if not row:
        return await cq.message.edit_text("❗ Заявка не найдена или уже обработана.")

    partner_pk, amount, telegram_id = row

    await db.execute(
        "UPDATE partner_withdraw_requests SET status = 'approved' WHERE id = ?",
        (req_id,), commit=True
    )
    await db.execute(
        """
        INSERT INTO partner_wallet_ops (partner_id, type, amount, src)
        VALUES (?, 'debit', ?, 'withdraw_confirmed')
        """,
        (partner_pk, amount), commit=True
    )
    await cq.message.edit_text(f"✅ Заявка #{req_id} одобрена, списано {amount:.2f} ₽.")

    if telegram_id:
        try:
            new_balance = await get_partner_balance(db, partner_pk)
            await cq.bot.send_message(
                telegram_id,
                (
                    f"✅ Ваша заявка #{req_id} на {amount:.2f} ₽ подтверждена!\n"
                    f"💳 Ваш обновлённый баланс: {new_balance:.2f} ₽"
                )
            )
        except Exception:
            logging.exception(f"Не удалось уведомить партнёра {telegram_id}")

# ─── 3) Отклонение заявки ───
@admin_withdraw_router.callback_query(F.data.startswith("withdraw_reject:"))
async def admin_reject(cq: types.CallbackQuery):
    await cq.answer()
    req_id = int(cq.data.split(":")[1])

    row = await db.execute(
        """
        SELECT wr.partner_id, wr.amount, p.telegram_id
          FROM partner_withdraw_requests AS wr
     LEFT JOIN partners AS p ON p.id = wr.partner_id
         WHERE wr.id = ? AND wr.status = 'pending'
        """,
        (req_id,), fetch="one"
    )
    if not row:
        return await cq.message.edit_text("❗ Заявка не найдена или уже обработана.")

    partner_pk, amount, telegram_id = row

    await db.execute(
        "UPDATE partner_withdraw_requests SET status = 'rejected' WHERE id = ?",
        (req_id,), commit=True
    )
    await db.execute(
        """
        INSERT INTO partner_wallet_ops (partner_id, type, amount, src)
        VALUES (?, 'credit', ?, 'withdraw_refund')
        """,
        (partner_pk, amount), commit=True
    )
    await cq.message.edit_text(f"❌ Заявка #{req_id} отклонена, {amount:.2f} ₽ возвращено.")

    if telegram_id:
        try:
            new_balance = await get_partner_balance(db, partner_pk)
            await cq.bot.send_message(
                telegram_id,
                (
                    f"❌ Ваша заявка #{req_id} на {amount:.2f} ₽ отклонена.\n"
                    f"Средства возвращены на ваш баланс.\n"
                    f"💳 Ваш обновлённый баланс: {new_balance:.2f} ₽"
                )
            )
        except Exception:
            logging.exception(f"Не удалось уведомить партнёра {telegram_id}")
