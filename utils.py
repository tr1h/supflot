# utils.py
from aiogram import types

MAX_MSG_LEN = 4000

async def safe_answer(msg: types.Message, text: str, **kwargs):
    """
    Разбивает text на фрагменты <= MAX_MSG_LEN и отправляет их по очереди.
    Все дополнительные kwargs (reply_markup, parse_mode и т.д.) передаются в answer().
    """
    while text:
        chunk, text = text[:MAX_MSG_LEN], text[MAX_MSG_LEN:]
        await msg.answer(chunk, **kwargs)
