from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import REVIEW_CHANNEL

router = Router()
REVIEW_URL = f"https://t.me/{REVIEW_CHANNEL.lstrip('@')}"

@router.message(Command("review"))
@router.message(F.text == "🌟 Отзывы")
async def go_to_review_channel(message: types.Message):
    """
    Перенаправляет пользователя в канал отзывов с кнопкой-ссылкой.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Перейти в канал отзывов", url=REVIEW_URL)
    kb.adjust(1)
    await message.answer(
        "Спасибо за желание оставить отзыв!\n\n"
        f"Все отзывы мы собираем в канале {REVIEW_CHANNEL}.\n"
        "После перехода нажмите «Написать сообщение» и оставьте там свой отзыв.\n\n"
        "⚠️ Обратите внимание: отзывы, присланные в этот чат боту, не сохраняются автоматически — публикуйте их в канале.",
        reply_markup=kb.as_markup()
    )

__all__ = ["router"]
