import os
import sqlite3
import logging

from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import DB_NAME  # путь к вашей sqlite‑базе

logger = logging.getLogger(__name__)
review_router = Router()

# создаём таблицу, если её ещё нет
def _init_reviews_table():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        rating     INTEGER,
        text       TEXT    NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

_init_reviews_table()

# Ссылка на ваш канал отзывов
REVIEW_CHANNEL = "@supflot_reviews"
REVIEW_URL     = f"https://t.me/{REVIEW_CHANNEL.lstrip('@')}"

@review_router.message(F.text == "🌟 Отзывы", F.chat.type == "private")
async def go_to_review_channel(message: types.Message):
    """
    При нажатии на кнопку «🌟 Отзывы» в личном чате даём
    ссылку-кнопку на канал и понятно объясняем, что отзыв
    нужно оставить именно там.
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📢 Перейти в канал отзывов", url=REVIEW_URL)
    ]])
    await message.answer(
        "Спасибо за желание оставить отзыв!\n\n"
        f"Все отзывы мы собираем в канале {REVIEW_CHANNEL}.\n"
        "После перехода нажмите «Написать сообщение» и оставьте там свой отзыв.\n\n"
        "⚠️ Обратите внимание: отзывы, присланные в этот чат боту, "
        "не сохраняются автоматически — публикуйте их в канале.",
        reply_markup=kb
    )

# Убираем весь остальной «пересылающий» код,
# чтобы не было ложных попыток отправить в канал из лички.

def register_review_handlers(dp_router: Router, db):
    """
    В run_bot.py:
        register_review_handlers(dp, db)
        dp.include_router(review_router)
    """
    pass

__all__ = ["review_router", "register_review_handlers"]
