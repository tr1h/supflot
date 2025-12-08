from aiogram import Router, types
from aiogram.filters import Command
from keyboards import main_menu  # или user_main_menu

partner_router = Router()

def register_partner_handlers(router: Router, db):
    @router.message(Command("partner"))
    async def apply_for_partner(msg: types.Message):
        user_id = msg.from_user.id

        # проверка — уже подавал?
        row = await db.execute("SELECT 1 FROM partner_requests WHERE user_id = ?", (user_id,), fetch="one")
        if row:
            return await msg.answer("🕓 Ваша заявка уже на рассмотрении.", reply_markup=main_menu())

        await db.execute(
            "INSERT INTO partner_requests (user_id, status) VALUES (?, ?)",
            (user_id, 'pending'),
            commit=True
        )
        await msg.answer("✅ Заявка партнёра отправлена! Мы свяжемся с вами.", reply_markup=main_menu())
