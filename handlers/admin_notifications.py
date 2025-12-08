import logging
from aiogram import Router, Bot, types
from aiogram.utils.keyboard import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS           # ADMIN_IDS = [12345678, 87654321]
from core.database import Database     # ваш класс для работы с БД

logger = logging.getLogger(__name__)

admin_notifications_router = Router()


async def notify_admins(booking_id: int, info: str, bot: Bot):
    """
    Разослать всем ADMIN_IDS сообщение о новой броне
    с кнопками «✅ Принять» / «❌ Отклонить».
    """
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"admin_accept_{booking_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin_reject_{booking_id}"
            )
        ]
    ])
    text = f"🆕 Новая бронь #{booking_id}\n\n{info}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")


def register_admin_notifications(router: Router, db: Database):
    """
    Регистрирует обработчики для коллбэков admin_accept_* и admin_reject_*.
    """

    @router.callback_query(
        lambda c: c.from_user.id in ADMIN_IDS
                  and c.data
                  and c.data.startswith("admin_accept_")
    )
    async def admin_accept_callback(callback: types.CallbackQuery):
        await callback.answer()  # чтобы у клиента пропало “колёсико”

        booking_id = int(callback.data.rsplit("_", 1)[1])
        # проверяем, что бронь ещё ожидает
        row = await db.execute(
            "SELECT status, user_id FROM bookings WHERE id = ?",
            (booking_id,),
            fetch=True
        )
        if not row:
            return await callback.answer("❌ Бронь не найдена.", show_alert=True)

        status, user_id = row
        if not status.startswith("waiting"):
            return await callback.answer("Эту бронь уже обработали.", show_alert=True)

        # подтверждаем бронь
        await db.execute(
            "UPDATE bookings SET status = 'active' WHERE id = ?",
            (booking_id,), commit=True
        )

        # убираем кнопки из админского сообщения
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass

        await callback.answer("✅ Бронь подтверждена.", show_alert=True)
        try:
            await callback.bot.send_message(
                user_id,
                f"✅ Ваша бронь #{booking_id} подтверждена администратором."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")


    @router.callback_query(
        lambda c: c.from_user.id in ADMIN_IDS
                  and c.data
                  and c.data.startswith("admin_reject_")
    )
    async def admin_reject_callback(callback: types.CallbackQuery):
        await callback.answer()

        booking_id = int(callback.data.rsplit("_", 1)[1])
        row = await db.execute(
            "SELECT status, user_id FROM bookings WHERE id = ?",
            (booking_id,),
            fetch=True
        )
        if not row:
            return await callback.answer("❌ Бронь не найдена.", show_alert=True)

        status, user_id = row
        if not status.startswith("waiting"):
            return await callback.answer("Эту бронь уже обработали.", show_alert=True)

        # отклоняем бронь
        await db.execute(
            "UPDATE bookings SET status = 'canceled' WHERE id = ?",
            (booking_id,), commit=True
        )

        # убираем кнопки
        try:
            await callback.message.edit_reply_markup()
        except Exception:
            pass

        await callback.answer("❌ Бронь отклонена.", show_alert=True)
        try:
            await callback.bot.send_message(
                user_id,
                f"❌ Ваша бронь #{booking_id} отклонена администратором."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")


__all__ = [
    "admin_notifications_router",
    "register_admin_notifications",
    "notify_admins",
]
