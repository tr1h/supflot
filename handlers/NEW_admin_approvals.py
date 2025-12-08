# -*- coding: utf-8 -*-
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards import admin_main_menu as admin_menu


def register_admin_approvals(router: Router, db, bot):
    # ---------- Меню заявок ----------
    @router.message(F.text == "✅ Одобрения партнёров")
    async def approve_partners_menu(msg: types.Message):
        rows = await db.execute("""
            SELECT id, name, telegram_id, COALESCE(contact_email, '—')
            FROM partners
            WHERE is_approved = 0
        """, fetchall=True)

        if not rows:
            return await msg.answer("📭 Нет новых заявок на одобрение.", reply_markup=admin_menu())

        for partner_id, name, tg_id, email in rows:
            text = (
                f"📝 Заявка от: <b>{name or 'Без имени'}</b>\n"
                f"🆔 TG ID: <code>{tg_id}</code>\n"
                f"📧 Email: {email}"
            )
            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Одобрить", callback_data=f"approve_partner_{partner_id}")
            kb.adjust(1)
            await msg.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

    # ---------- Колбэк одобрения ----------
    @router.callback_query(F.data.startswith("approve_partner_"))
    async def approve_partner_callback(cq: CallbackQuery):
        partner_id = int(cq.data.split("_")[-1])

        row = await db.execute(
            "SELECT telegram_id FROM partners WHERE id = ? AND is_approved = 0",
            (partner_id,), fetch=True
        )
        if not row:
            await cq.answer("❌ Не найдено или уже одобрено.", show_alert=True)
            return

        tg_id = row[0]

        await db.execute(
            "UPDATE partners SET is_approved = 1 WHERE id = ?",
            (partner_id,), commit=True
        )

        try:
            await bot.send_message(
                tg_id,
                "🎉 Ваша заявка одобрена! Вы стали партнёром SUPFLOT.",
                reply_markup=partner_main_menu()
            )
        except Exception as e:
            print(f"❗ Не смог отправить сообщение партнёру {tg_id}: {e!r}")

        await cq.message.edit_text("✅ Партнёр одобрен.")
        await cq.answer()
