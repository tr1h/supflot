from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from keyboards.admin import admin_menu

admin_partners_router = Router()

# --- Пример одной заглушки (в будущем сюда добавим функционал) ---
async def approve_partners_menu(message: types.Message, state: FSMContext):
    await message.answer("Раздел партнёров пока в разработке.", reply_markup=admin_menu())

def register_admin_partners(router: Router, db):
    router.message.register(approve_partners_menu, F.text == "👥 Одобрение партнёров")

__all__ = ["register_admin_partners", "admin_partners_router"]
