import logging

from aiogram import Router, types

from config import ADMIN_IDS
from services.booking_service import BookingService
from keyboards.admin import admin_menu

logger = logging.getLogger(__name__)
notifications_router = Router()


@notifications_router.callback_query(
    lambda c: c.from_user.id in ADMIN_IDS
              and c.data
              and c.data.startswith("admin_accept_")
)
async def admin_accept_callback(callback: types.CallbackQuery):
    await callback.answer()
    booking_id = int(callback.data.rsplit("_", 1)[1])
    updated = await BookingService.update_booking_status(
        db=callback.bot.db,
        booking_id=booking_id,
        status="active"
    )
    if not updated:
        return await callback.answer("Эту бронь уже обработали или не найдена.", show_alert=True)
    try:
        await callback.message.edit_reply_markup()
    except Exception as e:
        logger.debug(f"Failed to remove inline keyboard: {e}")
    booking = await BookingService.get_booking(callback.bot.db, booking_id)
    if booking:
        try:
            await callback.bot.send_message(
                booking["user_id"],
                f"✅ Ваша бронь #{booking_id} подтверждена администратором!"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {booking['user_id']}: {e}")
    await callback.message.answer(f"✅ Бронь #{booking_id} подтверждена", reply_markup=admin_menu())


@notifications_router.callback_query(
    lambda c: c.from_user.id in ADMIN_IDS
              and c.data
              and c.data.startswith("admin_reject_")
)
async def admin_reject_callback(callback: types.CallbackQuery):
    await callback.answer()
    booking_id = int(callback.data.rsplit("_", 1)[1])
    updated = await BookingService.update_booking_status(
        db=callback.bot.db,
        booking_id=booking_id,
        status="canceled"
    )
    if not updated:
        return await callback.answer("Эту бронь уже обработали или не найдена.", show_alert=True)
    try:
        await callback.message.edit_reply_markup()
    except Exception as e:
        logger.debug(f"Failed to remove inline keyboard: {e}")
    booking = await BookingService.get_booking(callback.bot.db, booking_id)
    if booking:
        try:
            await callback.bot.send_message(
                booking["user_id"],
                f"❌ Ваша бронь #{booking_id} отклонена администратором."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {booking['user_id']}: {e}")
    await callback.message.answer(f"❌ Бронь #{booking_id} отклонена", reply_markup=admin_menu())
