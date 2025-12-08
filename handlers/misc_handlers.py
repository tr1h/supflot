# handlers/misc_handlers.py
# -*- coding: utf-8 -*-

from aiogram import Router, types, F

router = Router(name="misc")

HELP_TEXT = (
    "🤖 *SUPBot* — ваш надёжный помощник по аренде SUP-досок.\n\n"
    "• `/start` — начать работу с ботом\n"
    "• `/daily` — суточная аренда досок\n"
    "• `/partner` — партнёрская панель\n"
    "• `/contacts` — контакты службы поддержки\n"
    "• `/offer` — оферта\n"
)
CONTACTS_TEXT = (
    "📞 *Контакты службы поддержки*\n\n"
    "Telegram: @supflot_support\n"
    "E-mail: support@supflot.pro\n"
)
OFFER_TEXT = (
    "📜 *Оферта*\n\n"
    "1. Используя бот, вы соглашаетесь с нашими правилами.\n"
    "2. Аренда досок оплачивается заранее.\n"
    "3. Отмена брони — не позднее чем за 2 часа до начала.\n"
    "4. Подробные условия: https://supflot.pro/offer\n"
)

# /help или кнопка "Помощь"
@router.message(F.text == "Помощь")
@router.message(F.text == "/help")
async def cmd_help(msg: types.Message):
    await msg.answer(HELP_TEXT, parse_mode="Markdown")

# кнопка / команда "Контакты"
@router.message(F.text == "Контакты")
@router.message(F.text == "/contacts")
async def cmd_contacts(msg: types.Message):
    await msg.answer(CONTACTS_TEXT, parse_mode="Markdown")

# кнопка / команда "Оферта"
@router.message(F.text == "Оферта")
@router.message(F.text == "/offer")
async def cmd_offer(msg: types.Message):
    await msg.answer(OFFER_TEXT, parse_mode="Markdown")
