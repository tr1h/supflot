# handlers/admin_bookings_handlers.py
# -*- coding: utf-8 -*-
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import new_admin_menu as admin_menu, new_main_menu as user_menu

logger = logging.getLogger(__name__)

admin_bookings_router = Router()


def admin_booking_keyboard(booking_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{booking_id}")
    kb.button(text="❌ Отменить",   callback_data=f"admin_cancel:{booking_id}")
    kb.adjust(2)
    return kb.as_markup()


def register_admin_bookings(router: Router, db):
    async def is_admin(uid: int) -> bool:
        row = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (uid,), fetch="one")
        return bool(row)

    # 📋 Все брони
    @router.message(F.text == "📋 Все брони")
    async def list_bookings(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Нет доступа", reply_markup=user_menu())

        rows = await db.execute(
            """
            SELECT b.id, b.user_id, b.board_id, b.date, b.start_time, b.start_minute,
                   b.duration, b.quantity, b.amount, b.status, b.payment_method,
                   COALESCE(br.name,'?') as board_name
            FROM bookings b
            LEFT JOIN boards br ON br.id = b.board_id
            WHERE b.status IN ('waiting_card','waiting_cash','active','finished')
            ORDER BY b.id DESC
            LIMIT 30
            """,
            fetchall=True
        )

        if not rows:
            return await msg.answer("Нет бронирований.", reply_markup=admin_menu())

        for row in rows:
            (bid, user_id, board_id, date_iso, start_h, start_m,
             duration, qty, amount, status, pay_method, board_name) = row

            start_time_str = f"{start_h:02}:{start_m:02}"
            text = (
                f"#{bid} — {board_name}\n"
                f"👤 User: {user_id}\n"
                f"📅 {date_iso} {start_time_str} ({duration} ч)\n"
                f"🔢 Кол-во: {qty}\n"
                f"💰 Сумма: {amount:.2f} ₽\n"
                f"💳 Оплата: {pay_method or '—'}\n"
                f"📌 Статус: {status}"
            )
            if status in ("waiting_card", "waiting_cash"):
                await msg.answer(text, reply_markup=admin_booking_keyboard(bid))
            else:
                await msg.answer(text)

        await msg.answer("Готово.", reply_markup=admin_menu())

    # ✅ Подтвердить
    @router.callback_query(F.data.startswith("admin_confirm:"))
    async def admin_confirm_booking(cq: CallbackQuery):
        logger.info(f"[CONFIRM] {cq.from_user.id} → {cq.data}")
        if not await is_admin(cq.from_user.id):
            return await cq.answer("⛔ Нет доступа", show_alert=True)

        bid = int(cq.data.split(":")[1])

        row = await db.execute(
            "SELECT user_id, board_id, date, start_time, start_minute FROM bookings WHERE id=?",
            (bid,), fetch="one"
        )
        if not row:
            return await cq.answer("Не найдено.", show_alert=True)

        user_id, board_id, date_iso, start_h, start_m = row

        await db.execute("UPDATE bookings SET status='active' WHERE id=?", (bid,), commit=True)
        await cq.answer("✅ Подтверждено")

        if cq.message:
            try:
                await cq.message.edit_text(cq.message.text + "\n\n✅ Подтверждено.")
            except Exception:
                pass

        try:
            start_time_str = f"{start_h:02}:{start_m:02}"
            await cq.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ Ваша бронь #{bid} подтверждена!\n"
                    f"Дата: {date_iso} {start_time_str}\n"
                    "Хорошего катания!"
                )
            )
        except Exception as e:
            logger.warning(f"Не отправилось сообщение пользователю {user_id}: {e!r}")

    # ❌ Отменить
    @router.callback_query(F.data.startswith("admin_cancel:"))
    async def admin_cancel_booking(cq: CallbackQuery):
        logger.info(f"[CANCEL] {cq.from_user.id} → {cq.data}")
        if not await is_admin(cq.from_user.id):
            return await cq.answer("⛔ Нет доступа", show_alert=True)

        bid = int(cq.data.split(":")[1])
        row = await db.execute("SELECT user_id FROM bookings WHERE id=?", (bid,), fetch="one")
        await db.execute("UPDATE bookings SET status='canceled' WHERE id=?", (bid,), commit=True)
        await cq.answer("❌ Отменено")
        if cq.message:
            try:
                await cq.message.edit_text(cq.message.text + "\n\n❌ Отменено.")
            except Exception:
                pass

        if row:
            try:
                await cq.bot.send_message(
                    chat_id=row[0],
                    text=f"❌ Ваша бронь #{bid} отменена администратором."
                )
            except Exception as e:
                logger.warning(f"Не отправилось сообщение пользователю {row[0]}: {e!r}")

    # Fallback для любых неизвестных callback'ов из админки (для отладки)
    @router.callback_query()
    async def fallback(cq: CallbackQuery):
        logger.warning(f"🔴 Unhandled callback: {cq.data}")
        await cq.answer("❓ Неизвестная кнопка")
