# handlers/notifications.py
# -*- coding: utf-8 -*-
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS

async def notify_admin_new_booking(bot: Bot, booking_id: int, booking_info: str):
    """
    Рассылает админу уведомление о новой брони с кнопками Подтвердить/Отклонить.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_accept_booking:{booking_id}"),
        InlineKeyboardButton("❌ Отклонить",   callback_data=f"admin_reject_booking:{booking_id}")
    )
    text = f"📌 <b>Новая бронь #{booking_id}</b>\n\n{booking_info}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass

async def notify_admin_new_partner(bot: Bot, partner_id: int, partner_name: str, telegram_id: int):
    """
    Уведомляет админу о новой заявке на партнёрство.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_partner:{partner_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_partner:{partner_id}")
    )
    text = (
        f"👤 <b>Новая заявка партнёра</b>\n\n"
        f"ID: {partner_id}\n"
        f"Название: {partner_name}\n"
        f"Telegram ID: {telegram_id}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass

async def notify_partner_booking_request(bot: Bot, partner_telegram_id: int, booking_id: int, booking_info: str):
    """
    Сообщает партнёру, что по его локации/доскам поступила новая бронь.
    """
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Принять бронирование", callback_data=f"partner_accept_booking:{booking_id}"),
        InlineKeyboardButton("❌ Отклонить",           callback_data=f"partner_reject_booking:{booking_id}")
    )
    text = f"📝 <b>Новая бронь #{booking_id}</b>\n\n{booking_info}"
    await bot.send_message(partner_telegram_id, text, reply_markup=kb, parse_mode="HTML")
