from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

def register_admin_payments(router: Router, db, bot):
    @router.message(F.text == "✅ Подтвердить оплату (наличные)")
    async def confirm_cash_payments(...): ...
    @router.message(F.text == "✅ Подтвердить оплату (карта)")
    async def confirm_card_payments(...): ...
    @router.callback_query(F.data.startswith("admin_confirmpay_"))
    async def admin_confirm_payment(...): ...
