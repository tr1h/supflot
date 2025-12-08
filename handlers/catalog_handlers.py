# handlers/catalog_handlers.py

import re
from aiogram import Router, F, types, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import PAYMENTS_PROVIDER_TOKEN

catalog_router = Router()


class AdBookingState(StatesGroup):
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
        kb.button(text="Подробнее",    callback_data=f"ad:show:{aid}")
        kb.button(text="🏄 Забронировать", callback_data=f"ad:book:{aid}")
        kb.adjust(2)
        if photo_id:
            await msg.answer_photo(photo_id, caption=caption, parse_mode="HTML", reply_markup=kb.as_markup())
        else:
            await msg.answer(caption, parse_mode="HTML", reply_markup=kb.as_markup())


# Подробнее по объявлению
@catalog_router.callback_query(F.data.regexp(r"^ad:show:(\d+)$"))
async def show_ad_detail(cq: types.CallbackQuery):
    await cq.answer()
    aid = int(re.match(r"^ad:show:(\d+)$", cq.data).group(1))
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
    kb.button(text="⬅️ К списку",        callback_data="ad:back")
    kb.adjust(2)
    if photo_id:
        await cq.message.answer_photo(photo_id, caption=text, parse_mode="HTML", reply_markup=kb.as_markup())
    else:
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())


# Назад к списку
@catalog_router.callback_query(F.data == "ad:back")
async def back_to_list(cq: types.CallbackQuery):
    await cq.answer()
    await show_ads_catalog(cq.message)


# Начало бронирования
@catalog_router.callback_query(F.data.regexp(r"^ad:book:(\d+)$"))
async def confirm_ad_booking(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    aid = int(re.match(r"^ad:book:(\d+)$", cq.data).group(1))
    db = cq.bot.db
    ad = await db.execute(
        "SELECT title, description, price_daily, address, partner_id, photo_file_id "
        "FROM partner_ads WHERE id=?", (aid,), fetch=True
    )
    if not ad:
        return await cq.message.answer("❌ Объявление не найдено.")
    title, desc, price, addr, partner_id, photo_id = ad
    text = (
        f"📝 Вы выбрали объявление:\n"
        f"📢 <b>{title}</b>\n"
        f"{desc}\n"
        f"📍 {addr or '—'}\n"
        f"💰 <b>{price:.0f}₽/сут</b>\n\n"
        "Перейти к оплате?"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"ad:confirm:{aid}")
    kb.button(text="❌ Отменить",    callback_data="ad:cancel")
    kb.adjust(2)
    if photo_id:
        await cq.message.answer_photo(photo_id, caption=text, parse_mode="HTML", reply_markup=kb.as_markup())
    else:
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await state.set_state(AdBookingState.waiting_confirm)
    await state.update_data(ad_id=aid, amount=price, partner_id=partner_id, ad_title=title)


# Выбор способа оплаты
@catalog_router.callback_query(F.data.regexp(r"^ad:confirm:(\d+)$"), AdBookingState.waiting_confirm)
async def choose_payment(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Telegram Pay", callback_data="pay_telegram")
    kb.button(text="💸 На карту",      callback_data="pay_card")
    kb.button(text="💵 Наличными",     callback_data="pay_cash")
    kb.button(text="❌ Отменить",      callback_data="ad:cancel")
    kb.adjust(1)
    await cq.message.answer("Спасибо! Выберите способ оплаты:", reply_markup=kb.as_markup())
    await state.set_state(AdBookingState.waiting_payment)


# Telegram‑оплата
@catalog_router.callback_query(F.data == "pay_telegram", AdBookingState.waiting_payment)
async def pay_telegram(cq: types.CallbackQuery, state: FSMContext, bot: Bot):
    await cq.answer()
    data = await state.get_data()
    amount_rub = data.get("amount", 0)
    if amount_rub <= 0:
        return await cq.message.answer("❌ Неверная сумма.")
    amount_cents = int(amount_rub * 100)
    desc    = f"P2P: {data.get('ad_title','')}"
    payload = f"p2p_{cq.from_user.id}_{data.get('ad_id')}"
    await bot.send_invoice(
        chat_id=cq.from_user.id,
        title="Оплата аренды",
        description=desc,
        payload=payload,
        provider_token=PAYMENTS_PROVIDER_TOKEN,
        currency="RUB",
        prices=[types.LabeledPrice(label="Аренда", amount=amount_cents)],
        start_parameter="booking",
        need_email=False,
        send_email_to_provider=False,
    )


# Успешная Telegram‑оплата
@catalog_router.message(F.successful_payment)
async def payment_success(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    db   = msg.bot.db
    partner = await db.execute(
        "SELECT contact_email, telegram_id FROM partners WHERE id=?",
        (data.get("partner_id"),), fetch=True
    )
    if partner and partner[0]:
        contact = partner[0]
    elif partner and partner[1]:
        contact = f"@{partner[1]}"
    else:
        contact = "Контакты будут высланы отдельно"
    await msg.answer(
        f"✅ Оплата прошла успешно!\nКонтакты владельца: <code>{contact}</code>",
        parse_mode="HTML"
    )
    await state.clear()


# Оплата на карту
@catalog_router.callback_query(F.data == "pay_card", AdBookingState.waiting_payment)
async def pay_card(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    card_number = "1234 5678 9000 0000"  # или храните в БД
    text = (
        f"💳 Переведите на карту: <code>{card_number}</code>\n"
        "После перевода нажмите ✅"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оплачено", callback_data="card_paid")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    kb.adjust(1)
    await cq.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())


# Подтверждение оплаты картой
@catalog_router.callback_query(F.data == "card_paid", AdBookingState.waiting_payment)
async def card_paid(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    db   = cq.bot.db
    data = await state.get_data()
    partner = await db.execute(
        "SELECT contact_email, telegram_id FROM partners WHERE id=?",
        (data.get("partner_id"),), fetch=True
    )
    if partner and partner[0]:
        contact = partner[0]
    elif partner and partner[1]:
        contact = f"@{partner[1]}"
    else:
        contact = "Контакты будут высланы отдельно"
    await cq.message.answer(
        f"✅ Оплата подтверждена!\nКонтакты владельца: <code>{contact}</code>",
        parse_mode="HTML"
    )
    await state.clear()


# Оплата наличными
@catalog_router.callback_query(F.data == "pay_cash", AdBookingState.waiting_payment)
async def pay_cash(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оплачено", callback_data="cash_paid")
    kb.button(text="❌ Отменить", callback_data="ad:cancel")
    kb.adjust(1)
    await cq.message.answer(
        "💵 Оплата наличными при получении.\nПосле оплаты нажмите ✅",
        reply_markup=kb.as_markup()
    )


# Подтверждение оплаты наличными
@catalog_router.callback_query(F.data == "cash_paid", AdBookingState.waiting_payment)
async def cash_paid(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    db   = cq.bot.db
    data = await state.get_data()
    partner = await db.execute(
        "SELECT contact_email, telegram_id FROM partners WHERE id=?",
        (data.get("partner_id"),), fetch=True
    )
    if partner and partner[0]:
        contact = partner[0]
    elif partner and partner[1]:
        contact = f"@{partner[1]}"
    else:
        contact = "Контакты будут высланы отдельно"
    await cq.message.answer(
        f"✅ Оплата подтверждена!\nКонтакты владельца: <code>{contact}</code>",
        parse_mode="HTML"
    )
    await state.clear()


# Отмена
@catalog_router.callback_query(F.data == "ad:cancel")
async def cancel_ad_booking(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer("❌ Бронирование отменено", show_alert=True)
    await state.clear()
    await cq.message.answer("Бронирование отменено.")
