# -*- coding: utf-8 -*-
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database import Database
from helpers.wallet import get_partner_balance
from config import ADMIN_IDS  # список админов из конфига

# наш роутер
withdraw_router = Router()
db: Database = None

# FSM-состояние для ввода суммы
class WithdrawStates(StatesGroup):
    enter_amount = State()

# функция регистрации
def register_withdraw_handlers(dp: Router, database: Database):
    global db
    db = database
    dp.include_router(withdraw_router)

# 1) Старт диалога: запрос суммы
@withdraw_router.message(F.text == "💸 Запросить выплату")
async def start_withdraw(msg: types.Message, state: FSMContext):
    # Получаем внутренний partner_id (а не telegram_id)
    partner_id = await db.get_partner_id_by_telegram(msg.from_user.id)
    balance = await get_partner_balance(db, partner_id)

    if balance < 500:
        await msg.answer(
            "❌ Минимальная сумма для вывода — 500 ₽\n"
            f"💰 Ваш баланс: {balance:.2f} ₽"
        )
        from handlers.partner_cabinet import show_partner_cabinet
        return await show_partner_cabinet(msg, db)

    # проверяем заявки за последние 24 ч
    recent = await db.execute(
        """
        SELECT 1
          FROM partner_withdraw_requests
         WHERE partner_id = ?
           AND status = 'pending'
           AND created_at >= datetime('now','-1 day')
        """,
        (partner_id,), fetch="one"
    )
    if recent:
        await msg.answer("⏳ Вы уже подавали заявку на вывод за последние 24 ч.")
        from handlers.partner_cabinet import show_partner_cabinet
        return await show_partner_cabinet(msg, db)

    await state.set_state(WithdrawStates.enter_amount)
    await msg.answer(f"💰 Ваш баланс: {balance:.2f} ₽\nВведите сумму для вывода:")

# 2) Получили сумму, сохраняем заявку и уведомляем админов
@withdraw_router.message(WithdrawStates.enter_amount)
async def confirm_withdraw(msg: types.Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await msg.answer("❗ Введите корректную положительную сумму!")

    # Получаем partner_id по telegram_id
    partner_id = await db.get_partner_id_by_telegram(msg.from_user.id)
    balance = await get_partner_balance(db, partner_id)

    if amount > balance:
        await state.clear()
        await msg.answer(f"❌ Недостаточно средств. Баланс: {balance:.2f} ₽")
        from handlers.partner_cabinet import show_partner_cabinet
        return await show_partner_cabinet(msg, db)

    # 2.1) Сохраняем заявку в БД
    await db.execute(
        "INSERT INTO partner_withdraw_requests (partner_id, amount, status) VALUES (?, ?, 'pending')",
        (partner_id, amount),
        commit=True
    )

    # получаем ID только что созданной заявки
    last = await db.execute("SELECT last_insert_rowid()", fetch="one")
    request_id = last[0]

    # 2.2) Резервируем деньги
    await db.execute(
        "INSERT INTO partner_wallet_ops (partner_id, type, amount, src) VALUES (?, 'debit', ?, 'withdraw_pending')",
        (partner_id, amount),
        commit=True
    )

    # 2.3) Сообщаем партнёру
    await msg.answer(f"✅ Заявка #{request_id} на выплату {amount:.2f} ₽ создана и ожидает одобрения.")
    await state.clear()

    # 2.4) Рассылаем уведомление администраторам
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"withdraw_approve:{request_id}")
    kb.button(text="❌ Отклонить",   callback_data=f"withdraw_reject:{request_id}")
    kb.adjust(2)

    text = (
        f"💸 <b>Новая заявка на выплату</b>\n\n"
        f"Партнёр: {msg.from_user.full_name} ({msg.fromф_user.id})\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"ID заявки: {request_id}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await msg.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb.as_markup())
        except Exception:
            logging.exception(f"Не удалось уведомить админа {admin_id}")

__all__ = ["register_withdraw_handlers"]
