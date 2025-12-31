import logging

from aiogram import Router, types, F
from aiogram.filters import Command

from config import ADMIN_IDS
from services.booking_service import BookingService
from keyboards.admin import admin_boards_menu, admin_menu

logger = logging.getLogger(__name__)
bookings_router = Router()


def _format_booking(b):
    """Вспомогательная функция форматирования одной брони."""
    # рассчитываем строку времени
    sh = b['start_time']
    sm = b.get('start_minute', 0)
    dur = b['duration']
    start_min = sh * 60 + sm
    # длительность в минутах vs часах
    if dur <= 24:
        dur_min = dur * 60
        dur_str = f"{dur} ч"
    else:
        dur_min = dur
        if dur < 60:
            dur_str = f"{dur} мин"
        else:
            h, m = divmod(dur, 60)
            dur_str = f"{h} ч{(' ' + str(m) + ' мин') if m else ''}"
    end = start_min + dur_min
    eh, em = divmod(end, 60)
    pay_icon = "💳" if b['payment_method']=='card' else "💵"
    return (
        f"🆔 #{b['id']} — {b['board_name']} @ {b['location_name']}\n"
        f"👤 Клиент: <b>{b.get('full_name','—')}</b> (ID: {b['user_id']})\n"
        f"📞 Телефон: {b.get('phone','—')}\n"
        f"📅 {b['date']} {sh:02}:{sm:02}–{eh%24:02}:{em:02}\n"
        f"⏳ {dur_str} | Кол-во: {b['quantity']}\n"
        f"💰 {b['amount']:.2f} ₽ {pay_icon}\n"
        + "―"*20
    )

@bookings_router.message(F.text == "📋 Все брони")
async def all_bookings(message: types.Message):
    """Показывает все активные бронирования администраторам."""
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Доступ запрещён!", reply_markup=admin_menu())
    rows = await BookingService.list_all_bookings(message.bot.db)
    if not rows:
        return await message.answer("Нет активных бронирований.", reply_markup=admin_boards_menu())
    parts = ["📋 <b>Все активные бронирования:</b>"]
    for b in rows:
        parts.append(_format_booking(b))
    text = "\n".join(parts)
    await message.answer(text, parse_mode="HTML", reply_markup=admin_boards_menu())

__all__ = ["bookings_router"]
