"""Обработчики платежей"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from config import Config
from core.database import Database
from services.payment_service import PaymentService
from keyboards.user import get_payment_method_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)


def register_payment_handlers(router: Router, db: Database, bot=None, notification_service=None):
    """Регистрация обработчиков платежей"""
    payment_service = PaymentService()
    
    @router.pre_checkout_query()
    async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
        """Обработка pre-checkout запроса"""
        await pre_checkout_query.answer(ok=True)
    
    @router.message(F.successful_payment)
    async def successful_payment(message: Message):
        """Обработка успешного платежа через Telegram Payments"""
        payment = message.successful_payment
        booking_id = int(payment.invoice_payload)
        
        try:
            # Обновляем статус бронирования
            await db.execute(
                "UPDATE bookings SET status = 'active', payment_method = 'telegram', payment_id = ? WHERE id = ?",
                (payment.telegram_payment_charge_id, booking_id)
            )
            
            booking = await db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            
            # Проверяем, была ли это мгновенная бронь (дата = сегодня)
            booking_date = datetime.strptime(booking['date'], "%Y-%m-%d").date() if isinstance(booking['date'], str) else booking['date']
            is_instant = booking_date == date.today()
            
            # Для мгновенной брони - сразу активируем, не ждем подтверждения партнера
            # Сообщение будет одинаковым, но логика активации отличается
            text = "✅ <b>Оплата успешно проведена!</b>\n\n"
            text += f"Бронирование #{booking_id} активировано.\n"
            text += f"Доска: {booking['board_name']}\n"
            text += f"Дата: {booking['date']}\n"
            text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
            text += f"Длительность: {booking['duration']} минут\n\n"
            
            if is_instant:
                text += "⚡ <b>Мгновенная бронь активирована!</b>\n"
                text += "Бронирование готово к использованию."
            else:
                text += "Ожидайте подтверждения от партнера."
            
            await message.answer(text)
            
            # Отправляем уведомление партнеру
            if notification_service and booking.get('partner_id'):
                try:
                    await notification_service.notify_partner_new_booking(booking['partner_id'], booking_id)
                except Exception as e:
                    logger.error(f"Error sending notification to partner: {e}")
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
            await message.answer("❌ Произошла ошибка при обработке платежа. Обратитесь в поддержку.")
    
    @router.callback_query(F.data.startswith("payment:"))
    async def payment_method_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор способа оплаты"""
        await callback.answer()
        payment_method = callback.data.split(":")[1]
        data = await state.get_data()
        
        booking_id = data.get("booking_id")
        if not booking_id:
            await callback.message.edit_text("❌ Ошибка: бронирование не найдено.")
            return
        
        if payment_method == "telegram":
            # Telegram Payments
            booking = await db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            
            if not Config.PAYMENTS_PROVIDER_TOKEN:
                await callback.message.edit_text(
                    "❌ Telegram Payments не настроен. Выберите другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                return
            
            prices = [LabeledPrice(label="Бронирование SUP-доски", amount=payment_service.format_amount(booking['amount']))]
            
            # Формируем описание с информацией о времени оплаты
            from datetime import datetime
            description = f"Дата: {booking['date']}, Время: {booking['start_time']}:{booking['start_minute']:02d}, Длительность: {booking['duration']} мин."
            if booking.get('payment_deadline'):
                payment_deadline = datetime.fromisoformat(booking['payment_deadline']) if isinstance(booking['payment_deadline'], str) else booking['payment_deadline']
                deadline_str = payment_deadline.strftime("%H:%M")
                description += f"\n⏰ Оплата до {deadline_str}"
            
            try:
                await callback.message.answer_invoice(
                    title=f"Бронирование: {booking['board_name']}",
                    description=description,
                    payload=str(booking_id),
                    provider_token=Config.PAYMENTS_PROVIDER_TOKEN,
                    currency="RUB",
                    prices=prices,
                    start_parameter=str(booking_id),
                )
            except TelegramBadRequest as e:
                logger.error(f"Telegram Payments error: {e}")
                if "PAYMENT_PROVIDER_INVALID" in str(e):
                    await callback.message.edit_text(
                        "❌ Telegram Payments не настроен или токен неверный.\n"
                        "Выберите другой способ оплаты.",
                        reply_markup=get_payment_method_keyboard()
                    )
                else:
                    await callback.message.edit_text(
                        "❌ Ошибка при создании платежа. Выберите другой способ оплаты.",
                        reply_markup=get_payment_method_keyboard()
                    )
                return
            except Exception as e:
                logger.error(f"Error sending invoice: {e}")
                await callback.message.edit_text(
                    "❌ Ошибка при создании платежа. Выберите другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                return
            
        elif payment_method == "card":
            # YooKassa
            booking = await db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            
            if not Config.YK_SHOP_ID or not Config.YK_SECRET:
                await callback.message.edit_text(
                    "❌ YooKassa не настроен. Выберите другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                return
            
            try:
                payment_data = await payment_service.create_yookassa_payment(
                    amount=booking['amount'],
                    description=f"Бронирование SUP-доски #{booking_id}",
                    booking_id=booking_id,
                    return_url=f"{Config.MINIAPP_URL}booking/{booking_id}" if Config.MINIAPP_URL else None
                )
            except Exception as e:
                logger.error(f"Error creating YooKassa payment: {e}")
                await callback.message.edit_text(
                    "❌ Ошибка при создании платежа YooKassa. Проверьте настройки или выберите другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                return
            
            if payment_data:
                await db.execute(
                    "UPDATE bookings SET payment_id = ?, payment_method = 'card' WHERE id = ?",
                    (payment_data['payment_id'], booking_id)
                )
                
                text = "💳 <b>Оплата банковской картой</b>\n\n"
                text += f"Сумма: {booking['amount']:.2f}₽\n\n"
                text += "Перейдите по ссылке для оплаты:"
                await callback.message.edit_text(text)
                await callback.message.answer(
                    f"🔗 {payment_data['confirmation_url']}",
                    reply_markup=get_back_keyboard()
                )
            else:
                await callback.message.edit_text(
                    "❌ Ошибка при создании платежа. Попробуйте другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                
        elif payment_method == "card_transfer":
            # Перевод на карту
            booking = await db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            
            if not Config.PAYMENT_CARD_DETAILS or Config.PAYMENT_CARD_DETAILS.startswith("your_") or Config.PAYMENT_CARD_DETAILS.startswith("card_number"):
                await callback.message.edit_text(
                    "❌ Оплата переводом на карту временно недоступна.\nВыберите другой способ оплаты.",
                    reply_markup=get_payment_method_keyboard()
                )
                return
            
            # Получаем deadline для отображения
            payment_deadline = None
            if booking.get('payment_deadline'):
                from datetime import datetime
                payment_deadline = datetime.fromisoformat(booking['payment_deadline']) if isinstance(booking['payment_deadline'], str) else booking['payment_deadline']
            
            await db.execute(
                "UPDATE bookings SET status = 'waiting_card', payment_method = 'card_transfer' WHERE id = ?",
                (booking_id,)
            )
            
            text = "💵 <b>Оплата переводом на карту</b>\n\n"
            text += f"<b>Сумма к оплате: {booking['amount']:.2f}₽</b>\n\n"
            
            if payment_deadline:
                deadline_str = payment_deadline.strftime("%H:%M")
                text += f"⏰ <b>Время на оплату: до {deadline_str}</b>\n\n"
            
            text += f"<b>Реквизиты для перевода:</b>\n{Config.PAYMENT_CARD_DETAILS}\n\n"
            text += "⚠️ <b>Важно:</b>\n"
            text += "• После перевода отправьте скриншот чека или подтверждение администратору\n"
            text += "• Ваше бронирование будет активировано после подтверждения оплаты\n"
            text += f"• В комментарии к переводу укажите: Бронь #{booking_id}\n"
            if payment_deadline:
                text += f"• ⚠️ Бронирование будет отменено, если оплата не будет подтверждена до {deadline_str}"
            
            await callback.message.edit_text(text, reply_markup=get_back_keyboard())
            
        elif payment_method == "cash":
            # Наличные
            booking = await db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            
            # Получаем deadline для отображения
            payment_deadline = None
            if booking.get('payment_deadline'):
                from datetime import datetime
                payment_deadline = datetime.fromisoformat(booking['payment_deadline']) if isinstance(booking['payment_deadline'], str) else booking['payment_deadline']
            
            await db.execute(
                "UPDATE bookings SET status = 'waiting_cash', payment_method = 'cash' WHERE id = ?",
                (booking_id,)
            )
            
            text = "💵 <b>Оплата наличными</b>\n\n"
            text += "Вы будете оплачивать наличными при получении доски.\n"
            text += "Партнер подтвердит получение оплаты.\n\n"
            
            if payment_deadline:
                deadline_str = payment_deadline.strftime("%H:%M")
                text += f"⏰ <b>Время на подтверждение: до {deadline_str}</b>\n"
                text += f"⚠️ Бронирование будет отменено, если партнер не подтвердит его до {deadline_str}"
            
            await callback.message.edit_text(text, reply_markup=get_back_keyboard())
        
        await state.clear()

