# handlers/NEW_admin_payments.py

from aiogram import Router, types, F
from keyboards import new_admin_menu as admin_menu, new_main_menu as main_menu

admin_payments_router = Router()

def register_admin_payments(router: Router, db):

    async def is_admin(uid: int) -> bool:
        row = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (uid,), fetch="one")
        return bool(row)

    @router.message(F.text == "💳 Платежи")
    async def show_payments(msg: types.Message):
        if not await is_admin(msg.from_user.id):
            return await msg.answer("⛔ Нет доступа", reply_markup=main_menu())

        rows = await db.execute("""
            SELECT id, user_id, amount, payment_method, created_at
            FROM payments
            ORDER BY created_at DESC
            LIMIT 10
        """, fetchall=True)

        if not rows:
            return await msg.answer("Нет платежей за последнее время.", reply_markup=admin_menu())

        text = "💳 <b>Последние платежи:</b>\n\n"
        for pid, uid, amount, method, created in rows:
            method_icon = "💵" if method == "cash" else "💳"
            text += (
                f"ID: {pid} | 👤 {uid}\n"
                f"Сумма: {amount:.2f} ₽ {method_icon}\n"
                f"Дата: {created}\n"
                f"{'―'*20}\n"
            )

        await msg.answer(text, parse_mode="HTML", reply_markup=admin_menu())

__all__ = ["register_admin_payments", "admin_payments_router"]
