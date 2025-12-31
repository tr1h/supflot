import logging

from aiogram import Router, types, F
from aiogram.filters import Command

from config import ADMIN_IDS
from keyboards.admin import admin_menu

logger = logging.getLogger(__name__)
admin_base_router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора по списку ADMIN_IDS"""
    return user_id in ADMIN_IDS


@admin_base_router.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Обработчик команды /admin: открывает админ-панель"""
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Доступ запрещён!")
    await message.answer("👑 Админ-панель:", reply_markup=admin_menu())


@admin_base_router.message(F.text == "⬅️ Назад")
async def back_to_admin(message: types.Message):
    """Возврат в админ-панель из вложенных меню"""
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Доступ запрещён!")
    await message.answer("👑 Админ-панель:", reply_markup=admin_menu())

__all__ = ["admin_base_router"]
