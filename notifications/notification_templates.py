# notifications/notification_templates.py
from aiogram.utils.keyboard import InlineKeyboardBuilder


def new_booking_admin(booking_id, user_name, board_name, date, start_time, end_time, quantity, amount):
    return (
        "🆕 Новая бронь!\n"
        f"🔖 ID: {booking_id}\n"
        f"👤 Клиент: {user_name}\n"
        f"🏄 Доска: {board_name}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {start_time}:00 - {end_time}:00\n"
        f"🔢 Количество: {quantity}\n"
        f"💰 Сумма: {amount:.2f} ₽\n\n"
        "<a href='https://supflot.pro/admin/bookings'>Просмотреть в админке</a>"
    )


def new_booking_partner(booking_id, user_name, board_name, date, start_time, end_time, quantity, amount):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"partner_confirm:{booking_id}")
    kb.button(text="❌ Отклонить", callback_data=f"partner_reject:{booking_id}")

    return (
        "🆕 Новая бронь на вашу доску!\n"
        f"🔖 #{booking_id}\n"
        f"👤 {user_name}\n"
        f"🏄 {board_name}\n"
        f"📅 {date} {start_time}:00–{end_time}:00\n"
        f"🔢 {quantity} шт.\n"
        f"💰 {amount:.2f} ₽\n\n"
        "Подтвердите бронь:",
        kb.as_markup()
    )


def booking_confirmed_user(board_name, date, start_time, end_time):
    return (
        "✅ Ваша бронь подтверждена!\n"
        f"🏄 {board_name}\n"
        f"📅 {date} {start_time}:00–{end_time}:00\n\n"
        "Ждем вас на локации!"
    )


def booking_rejected_user():
    return (
        "❌ К сожалению, партнер отклонил вашу бронь.\n\n"
        "Пожалуйста, выберите другое время или доску."
    )


def reminder_before_start_user(start_time, end_time):
    return (
        "⏰ Напоминание: ваша бронь начинается через 1 час!\n"
        f"🏄 {start_time}:00–{end_time}:00\n\n"
        "Не забудьте взять с собой всё необходимое."
    )


def reminder_before_end_user(end_time):
    return (
        "⏳ Ваша бронь заканчивается через 30 минут!\n"
        f"🏄 До {end_time}:00\n\n"
        "Пожалуйста, подготовьтесь к возврату оборудования."
    )


def booking_finished():
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Оставить отзыв", callback_data="leave_review")

    return (
        "✅ Бронь завершена! Спасибо, что выбрали SUPFLOT.\n\n"
        "Пожалуйста, оставьте отзыв о качестве услуги.",
        kb.as_markup()
    )


def payment_success(amount):
    return f"✅ Платеж на сумму {amount:.2f} ₽ успешно завершен!"


def payment_failed():
    return "❌ Ошибка при обработке платежа. Пожалуйста, попробуйте еще раз."


def withdraw_requested(amount):
    return (
        f"🔄 Ваш запрос на выплату {amount:.2f} ₽ принят в обработку.\n"
        "Обычно выплаты занимают 1-3 рабочих дня."
    )


def new_withdraw_admin(partner_id, amount):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Обработать", callback_data=f"admin_withdraw:{partner_id}")

    return (
        f"💰 Новый запрос на выплату от партнера {partner_id}!\n"
        f"Сумма: {amount:.2f} ₽",
        kb.as_markup()
    )


def booking_reminder_partner(booking_id, time_left):
    times = {
        60: "1 час",
        30: "30 минут",
        15: "15 минут",
        5: "5 минут"
    }
    return f"⏳ Бронь #{booking_id} начнется через {times.get(time_left, f'{time_left} минут')}!"