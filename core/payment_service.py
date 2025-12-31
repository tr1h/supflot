# core/payment_service.py
from aiogram import Bot, types
from handlers.admin_notifications import notify_admins
from core.booking_service import BookingService

class PaymentService:
    @staticmethod
    def label(method: str) -> str:
        return {"telegram":"💳 Telegram Pay","card":"💸 На карту","cash":"💵 Наличными"}[method]

    @staticmethod
    async def start_payment(bot: Bot, chat_id: int, booking_data: dict, payment_method: str):
        amount = booking_data["amount"]
        # 1) если telegram‑invoice
        if payment_method=="telegram":
            # ... send_invoice, handle pre_checkout, successful_payment
            pass
        # 2) если card или cash — просто сохраняем в booking со статусом waiting_payment
        booking_id = await BookingService.create_booking(
            db=bot.db,
            **booking_data,
            payment_method=payment_method,
            status="waiting_payment"
        )
        # показываем юзеру инструкции по оплате, а после — оповещаем админов
        await bot.send_message(chat_id, f"Для оплаты {self.label(payment_method)} …")
        info = BookingService.format_booking_info(booking_id, booking_data)
        await notify_admins(booking_id, info, bot)
