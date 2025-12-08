# services/payment_service.py

import json
from aiogram import Bot, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, PreCheckoutQuery

from config import PAYMENTS_PROVIDER_TOKEN, PLATFORM_COMMISSION_PERCENT
from services.booking_service import BookingService
from services.notification_service import NotificationService


class PaymentService:
    @staticmethod
    async def start_payment(bot: Bot, chat_id: int, booking_data: dict, payment_method: str) -> int:
        """
        Запускает процесс оплаты:
        - Для 'telegram' шлёт инвойс и ждёт pre_checkout и successful_payment
        - Для 'card' и 'cash' создаёт бронь в БД со статусом waiting_<method>,
          отправляет инструкцию пользователю и уведомляет админов.
        Возвращает booking_id.
        """
        # Для Telegram‑Pay
        if payment_method == "telegram":
            amount = booking_data["amount"]
            cents = int(amount * 100)
            desc = (
                f"{booking_data['board_name']} "
                f"{booking_data['duration']} ч ×{booking_data['quantity']}"
            )
            payload = f"booking_{chat_id}_{int(types.datetime.datetime.now().timestamp())}"
            provider_data = {
                "receipt": {
                    "items": [{
                        "description": desc[:128],
                        "quantity": 1,
                        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                        "vat_code": 1,
                        "payment_mode": "full_payment",
                        "payment_subject": "commodity"
                    }],
                    "tax_system_code": 1
                }
            }
            # Отправка счёта
            await bot.send_invoice(
                chat_id=chat_id,
                title="Оплата бронирования",
                description=desc[:128],
                payload=payload,
                provider_token=PAYMENTS_PROVIDER_TOKEN,
                currency="RUB",
                prices=[LabeledPrice(label="Бронь", amount=cents)],
                start_parameter="booking",
                need_email=True,
                send_email_to_provider=True,
                provider_data=json.dumps(provider_data)
            )
            # здесь предполагается, что register_telegram_payments уже подключён к рутеру
            return None  # booking_id будет создан в successful_payment

        # Для карты и наличных: сразу создаём бронь со статусом ожидания
        booking_id = await BookingService.create_booking(
            db=bot.db,
            user_id=chat_id,
            board_id=booking_data["board_id"],
            date=booking_data["date"],
            start=booking_data.get("start") or booking_data.get("start_time"),
            duration=booking_data["duration"],
            quantity=booking_data["quantity"],
            amount=booking_data["amount"],
            payment_method=payment_method
        )
        # Инструкция для пользователя
        if payment_method == "card":
            await bot.send_message(
                chat_id,
                f"💸 Оплата на карту:\n\n{booking_data.get('card_details', 'Укажите реквизиты в настройках')}\n"
                "После перевода нажмите «✅ Оплачено»."
            )
        else:  # cash
            await bot.send_message(
                chat_id,
                "💵 Оплата наличными при получении. После оплаты нажмите «✅ Оплачено»."
            )

        # Уведомление админам
        summary = BookingService.format_summary(booking_data)
        await NotificationService.new_booking(bot, booking_id, summary)

        return booking_id

    @staticmethod
    async def pre_checkout_query_handler(pre: PreCheckoutQuery, bot: Bot):
        # Отвечаем на запрос
        await bot.answer_pre_checkout_query(pre.id, ok=True)

    @staticmethod
    async def successful_payment_handler(message: types.Message, state: FSMContext):
        # Вызывается после успешной Telegram‑оплаты
        data = await state.get_data()
        user_id = message.from_user.id
        # Создаём бронь сразу в active
        booking_id = await BookingService.create_booking(
            db=message.bot.db,
            user_id=user_id,
            board_id=data["board_id"],
            date=data["date"],
            start=data.get("start") or data.get("start_time"),
            duration=data["duration"],
            quantity=data["quantity"],
            amount=data["amount"],
            payment_method="telegram"
        )
        await message.answer("✅ Оплата прошла успешно! Ваша бронь активна.")
        # Уведомляем админам
        summary = BookingService.format_summary(data)
        await NotificationService.new_booking(message.bot, booking_id, summary)
        await state.clear()
