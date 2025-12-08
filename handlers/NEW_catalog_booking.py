# -*- coding: utf-8 -*-
"""
Каталог объявлений от партнёров: просмотр, бронирование, оплата.
"""

import re
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PAYMENTS_PROVIDER_TOKEN

catalog_router = Router()


class CatalogBookingState(StatesGroup):
    waiting_confirm = State()
    waiting_payment = State()


# Показать каталог
@catalog_router.message(F.text == "🛍️ Каталог объявлений")
async def show_ads_catalog(msg: types.Message):
    db = msg.bot.db
    ads = await db.execute(
        "SELECT id, title, description, price_daily, address, photo_file_id "
        "FROM partner_ads WHERE is_active=1 ORDER BY created_at DESC LIMIT 5",
        fetchall=True
    )
    if not ads:
        return await msg.answer("🛍️ Нет объявлений")

    for aid, title, desc, price, addr, photo_id in ads:
        caption = (
            f"📢 <b>{title}</b>\n"
            f"{desc}\n"
            f"📍 {addr or '—'}\n"
            f"💰 <b>{price:.0f}₽/сут</b>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="Подробнее", callback_data=f"ad:show:{aid}")
        kb.button(text="🏄 Забронировать", callback_data=f"ad:book:{aid}")
        kb.adjust(2)
        if photo_id:
            await msg.answer_photo(photo_id, caption=caption, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await msg.answer(caption, parse_mode="HTML", reply_markup=kb.as_markup())


# Подробнее
@catalog_router.callback_query(F.data.regexp(r"^ad:show:(\d+)$"))
async def show_detail(cq: types.CallbackQuery):
    await cq.answer()
    aid = int(cq.data.split(":")[2])
    db = cq.bot.db
    ad = await db.execute(
        "SELECT title, description, price_daily, address, photo_file_id "
        "FROM partner_ads WHERE id=?", (aid,), fetch=True
    )
    if not ad:
        return await cq.message.answer("❌ Объявление не найдено.")
    title, desc, price, addr, photo_id = ad
    text = (
        f"📢 <b>{title}</b>\n"
        f"{desc}\n"
        f"📍 {addr or '—'}\n"
        f"💰 <b>{price:.0f}₽/сут</b>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🏄 Забронировать", callback_data=f"ad:book:{aid}")
    kb.button(text="⬅️ Назад", callback_data="ad:back")
    kb.adjust(2)
    await cq.message.answer_photo(photo_id, caption=text, parse_mode="HTML", reply_markup=kb.as_markup())


@catalog_router.callback_query(F.data == "ad:back")
async def back_to_catalog(cq: types.CallbackQuery):
    await cq.answer()
    await show_ads_catalog(cq.message)


# Начало бронирования
@catalog_router.callback_query(F.data.regexp(r"^ad:book:(\d+)$"))
async def confirm_booking(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    aid = int(cq.data.split(":")[2])
    db = cq.bot.db
    ad = await db.execute(
        "SELECT title, description, price_daily, address, partner_id, photo_file_id "
        "FROM partner_ads WHERE id=?", (aid,), fetch=True
    )
    if not ad:
        return await cq.message.answer("❌ Объявление не найдено.")
    title, desc, price, addr, partner_id, photo_id = ad
    await state.update_data(ad_id=aid, amount=price, partner_id=partner_id, ad_title=title)

    text = (
        f"📢 <b>{title}</b>\n"
        f"{desc}\n"
        f"📍 {addr or '—'}\n"
        f"💰 <b>{price:.0f}₽/сут</b>\n\n"
        "Перейти к оплате?"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="ad:confirm")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    kb.adjust(2)
    await cq.message.answer_photo(photo_id, caption=text, parse_mode="HTML", reply_markup=kb.as_markup())
    await state.set_state(CatalogBookingState.waiting_confirm)


# Подтвердили
@catalog_router.callback_query(F.data == "ad:confirm", CatalogBookingState.waiting_confirm)
async def choose_payment(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Telegram Pay", callback_data="pay_telegram")
    kb.button(text="💸 На карту", callback_data="pay_card")
    kb.button(text="💵 Наличными", callback_data="pay_cash")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    kb.adjust(1)
    await cq.message.answer("Выберите способ оплаты:", reply_markup=kb.as_markup())
    await state.set_state(CatalogBookingState.waiting_payment)


# Telegram Pay
@catalog_router.callback_query(F.data == "pay_telegram", CatalogBookingState.waiting_payment)
async def pay_telegram(cq: types.CallbackQuery, state: FSMContext, bot: Bot):
    await cq.answer()
    data = await state.get_data()
    amount_rub = data.get("amount", 0)
    payload = f"p2p_{cq.from_user.id}_{data.get('ad_id')}"
    await bot.send_invoice(
        chat_id=cq.from_user.id,
        title="Оплата аренды",
        description=f"Каталог: {data.get('ad_title')}",
        payload=payload,
        provider_token=PAYMENTS_PROVIDER_TOKEN,
        currency="RUB",
        prices=[types.LabeledPrice(label="Аренда", amount=int(amount_rub * 100))],
        start_parameter="catalog",
    )


# Telegram Pay успешная
@catalog_router.message(F.successful_payment)
async def success_pay(msg: types.Message, state: FSMContext):
    db = msg.bot.db
    data = await state.get_data()
    await save_booking(msg.bot, db, msg.from_user, data, "telegram")
    await msg.answer("✅ Оплата прошла успешно! Владелец скоро свяжется с вами.")
    await state.clear()


# Карта
@catalog_router.callback_query(F.data == "pay_card", CatalogBookingState.waiting_payment)
async def pay_card(cq: types.CallbackQuery):
    await cq.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оплачено", callback_data="card_paid")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    await cq.message.answer(
        "💳 Переведите на карту: <code>1234 5678 9000 0000</code>\nПосле перевода нажмите ✅",
        parse_mode="HTML", reply_markup=kb.as_markup()
    )


# Наличка
@catalog_router.callback_query(F.data == "pay_cash", CatalogBookingState.waiting_payment)
async def pay_cash(cq: types.CallbackQuery):
    await cq.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оплачено", callback_data="cash_paid")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    await cq.message.answer(
        "💵 Оплата наличными при получении. После оплаты нажмите ✅",
        reply_markup=kb.as_markup()
    )


# Подтверждение оплаты вручную
@catalog_router.callback_query(F.data.in_(("card_paid", "cash_paid")), CatalogBookingState.waiting_payment)
async def confirm_manual_payment(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    db = cq.bot.db
    data = await state.get_data()
    method = "card" if cq.data == "card_paid" else "cash"
    await save_booking(cq.bot, db, cq.from_user, data, method)
    await cq.message.answer("✅ Спасибо, данные переданы владельцу!")
    await state.clear()


# Отмена
@catalog_router.callback_query(F.data == "ad:cancel")
async def cancel_booking(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer("❌ Бронирование отменено", show_alert=True)
    await state.clear()
    await cq.message.answer("Бронирование отменено.")


# Сохраняем бронь и уведомляем
async def save_booking(bot: Bot, db, user, data, method: str):
    await db.execute(
        "INSERT INTO ad_bookings(ad_id, user_id, payment_method, created_at) VALUES (?, ?, ?, datetime('now'))",
        (data.get("ad_id"), user.id, method),
        commit=True
    )
    partner = await db.execute(
        "SELECT telegram_id FROM partners WHERE id=?", (data.get("partner_id"),), fetch=True
    )
    if partner and partner[0]:
        try:
            await bot.send_message(
                partner[0],
                f"🔔 <b>Новая бронь</b>\n"
                f"📢 {data.get('ad_title')}\n"
                f"👤 Пользователь: @{user.username or user.full_name}\n"
                f"💳 Оплата: {method}",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"⚠️ Ошибка уведомления владельца: {e}")
