# handlers/NEW_payments.py
# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import LabeledPrice, PreCheckoutQuery, CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from config import (
    PAYMENTS_PROVIDER_TOKEN,
    PAYMENT_CARD_DETAILS,
    PLATFORM_COMMISSION_PERCENT,
)
from handlers.admin_notifications import notify_admins
from handlers.NEW_states import BookingState
from keyboards.common import card_paid_keyboard, cash_paid_keyboard, main_menu

logger = logging.getLogger(__name__)
payments_router = Router()
db = None  # сюда придёт ваш Database


def register_payment_handlers(dp: Router, database):
    """
    Регистрируем роутер оплат и сохраняем ссылку на Database.
    """
    global db
    db = database
    dp.include_router(payments_router)


# ——— Telegram‐Invoice ———

@payments_router.callback_query(StateFilter(BookingState.select_payment), F.data == "pay_telegram")
async def pay_telegram(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    data = await state.get_data()

    # формируем описание
    days = data.get("days")
    dur  = data.get("duration")
    qty  = data.get("quantity", 1)
    name = data.get("board_name", "Доска")
    if days:
        desc = f"Суточная аренда: {name} — {days} дн."
    elif dur and 0 < dur < 24:
        desc = f"SUP-бронь: {name} — {dur}ч × {qty}"
    else:
        desc = f"SUP-бронь: {name}"

    amount = data.get("amount", 0.0)
    if amount <= 0:
        return await cq.message.answer("❌ Неверная сумма для оплаты.")
    cents = int(amount * 100)

    payload = f"booking_{cq.from_user.id}_{int(datetime.now().timestamp())}"
    provider_data = {
        "receipt": {
            "items": [{
                "description": desc[:128],
                "quantity": 1,
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }],
            "tax_system_code": 1
        }
    }

    try:
        await cq.bot.send_invoice(
            chat_id=cq.from_user.id,
            title="Оплата аренды",
            description=desc[:128],
            payload=payload,
            provider_token=PAYMENTS_PROVIDER_TOKEN,
            currency="RUB",
            prices=[LabeledPrice(label="Аренда", amount=cents)],
            start_parameter="sup-booking",
            need_email=True,
            send_email_to_provider=True,
            provider_data=json.dumps(provider_data),
        )
    except Exception as e:
        await cq.message.answer(f"❌ Не удалось создать счёт: {e}")


@payments_router.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    # подтверждаем телеграму что всё ок
    await pre.answer(ok=True)


@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    data      = await state.get_data()
    user_id   = message.from_user.id
    board_id  = data["board_id"]
    board_name= data["board_name"]
    date      = data["date"]
    st        = data.get("start_time", 0)
    mn        = data.get("start_minute", 0)
    dur       = data["duration"]
    qty       = data.get("quantity", 1)
    amount    = data["amount"]

    # 1) записываем бронь с локальным временем
    row = await db.execute(
        """
        INSERT INTO bookings (
          user_id, board_id, board_name,
          date, start_time, start_minute,
          duration, quantity, amount,
          status, payment_method, created_at
        ) VALUES (
          ?, ?, ?,
          ?, ?, ?,
          ?, ?, ?,
          'active', 'telegram', datetime('now','localtime')
        )
        RETURNING id
        """,
        (
            user_id, board_id, board_name,
            date, st, mn,
            dur, qty, amount
        ),
        fetch="one",
        commit=True
    )
    booking_id = row[0]

    # 2) зачисляем партнёру его долю (только online), сразу же
    share = amount * (1 - PLATFORM_COMMISSION_PERCENT / 100.0)
    pr = await db.execute(
        "SELECT partner_id FROM boards WHERE id = ?",
        (board_id,), fetch="one"
    )
    if pr:
        await db.execute(
            """
            INSERT INTO partner_wallet_ops (
              partner_id, type, amount, src, created_at
            ) VALUES (
              ?, 'credit', ?, 'booking_completed',
              datetime('now','localtime')
            )
            """,
            (pr[0], share),
            commit=True
        )

    # 3) отвечаем пользователю и чистим FSM
    await message.answer("✅ Оплата прошла успешно! Ваша бронь активна.", reply_markup=main_menu())
    await state.clear()


# ——— Оплата картой вручную ———

@payments_router.callback_query(StateFilter(BookingState.select_payment), F.data == "pay_card")
async def pay_card(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await cq.message.answer(
        f"💸 Оплата на карту:\n\n{PAYMENT_CARD_DETAILS}\n\nПосле перевода нажмите ✅",
        reply_markup=card_paid_keyboard()
    )
    await state.set_state(BookingState.wait_card_paid)


@payments_router.callback_query(StateFilter(BookingState.wait_card_paid), F.data == "card_paid")
async def card_paid(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    data      = await state.get_data()
    user_id   = cq.from_user.id
    board_id  = data["board_id"]
    board_name= data["board_name"]
    date      = data["date"]
    st        = data.get("start_time", 0)
    mn        = data.get("start_minute", 0)
    dur       = data["duration"]
    qty       = data.get("quantity", 1)
    amount    = data["amount"]

    row = await db.execute(
        """
        INSERT INTO bookings (
          user_id, board_id, board_name,
          date, start_time, start_minute,
          duration, quantity, amount,
          status, payment_method, created_at
        ) VALUES (
          ?, ?, ?,
          ?, ?, ?,
          ?, ?, ?,
          'waiting_card', 'card', datetime('now','localtime')
        )
        RETURNING id
        """,
        (
            user_id, board_id, board_name,
            date, st, mn,
            dur, qty, amount
        ),
        fetch="one",
        commit=True
    )
    bid = row[0]

    # уведомляем админов
    try:
        await notify_admins(bid, f"{date} {st:02}:{mn:02}", cq.bot)
    except Exception:
        logger.exception("Не удалось уведомить админов о card_paid")

    await cq.message.answer(f"✅ Бронь #{bid} создана! Ожидайте подтверждения.", reply_markup=main_menu())
    await state.clear()


# ——— Оплата наличными ———

@payments_router.callback_query(StateFilter(BookingState.select_payment), F.data == "pay_cash")
async def pay_cash(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await cq.message.answer(
        "📜 Оплата наличными при получении.\nПосле передачи денег нажмите ✅",
        reply_markup=cash_paid_keyboard()
    )
    await state.set_state(BookingState.wait_cash_paid)


@payments_router.callback_query(StateFilter(BookingState.wait_cash_paid), F.data == "cash_paid")
async def cash_paid(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    data      = await state.get_data()
    user_id   = cq.from_user.id
    board_id  = data["board_id"]
    board_name= data["board_name"]
    date      = data["date"]
    st        = data.get("start_time", 0)
    mn        = data.get("start_minute", 0)
    dur       = data["duration"]
    qty       = data.get("quantity", 1)
    amount    = data["amount"]

    row = await db.execute(
        """
        INSERT INTO bookings (
          user_id, board_id, board_name,
          date, start_time, start_minute,
          duration, quantity, amount,
          status, payment_method, created_at
        ) VALUES (
          ?, ?, ?,
          ?, ?, ?,
          ?, ?, ?,
          'waiting_cash', 'cash', datetime('now','localtime')
        )
        RETURNING id
        """,
        (
            user_id, board_id, board_name,
            date, st, mn,
            dur, qty, amount
        ),
        fetch="one",
        commit=True
    )
    bid = row[0]

    await cq.message.answer(f"✅ Бронь #{bid} создана! Ожидайте подтверждения.", reply_markup=main_menu())
    await state.clear()
