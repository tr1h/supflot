# handlers/wallet_handlers.py
from aiogram import Router, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

from core.database import Database
from helpers.wallet import get_partner_balance

router = Router()
db: Database = None

class WithdrawWalletFSM(StatesGroup):
    amount = State()

def register_wallet_handlers(dp: Router, database: Database):
    global db
    db = database
    dp.include_router(router)

@router.callback_query(F.data == "partner_wallet")
async def partner_wallet_menu(cq: types.CallbackQuery):
    await cq.answer()
    pid = await db.get_partner_id_by_telegram(cq.from_user.id)
    bal = await get_partner_balance(db, cq.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Запросить выплату", callback_data="partner_wallet_withdraw")
    kb.button(text="📜 История операций", callback_data="partner_wallet_history")
    kb.adjust(1)
    await cq.message.answer(
        f"💼 <b>Ваш кошелёк</b>\n\n{hbold('Баланс:')} {bal:.2f} ₽",
        reply_markup=kb.as_markup(), parse_mode="HTML"
    )

@router.callback_query(F.data == "partner_wallet_withdraw")
async def partner_wallet_withdraw(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    bal = await get_partner_balance(db, cq.from_user.id)
    if bal < 500:
        await cq.message.answer(f"❌ Мин. сумма — 500 ₽\nБаланс: {bal:.2f} ₽")
        return await partner_wallet_menu(cq)
    pid = await db.get_partner_id_by_telegram(cq.from_user.id)
    recent = await db.execute(
        "SELECT 1 FROM partner_withdraw_requests "
        "WHERE partner_id=? AND status='pending' "
        "AND created_at>=datetime('now','-1 day')",
        (pid,), fetch=True
    )
    if recent:
        await cq.message.answer("⏳ Уже был запрос за 24 ч.")
        return await partner_wallet_menu(cq)
    await state.set_state(WithdrawWalletFSM.amount)
    await cq.message.answer(f"💰 Баланс: {bal:.2f} ₽\nВведите сумму:")

@router.message(WithdrawWalletFSM.amount)
async def confirm_partner_wallet_withdraw(msg: types.Message, state: FSMContext):
    try:
        amt = float(msg.text.replace(",","."))
        if amt <= 0: raise ValueError
    except:
        return await msg.answer("❗ Некорректная сумма")
    pid = await db.get_partner_id_by_telegram(msg.from_user.id)
    bal = await get_partner_balance(db, msg.from_user.id)
    if amt > bal:
        await state.clear()
        return await msg.answer(f"❌ Недостаточно ({bal:.2f} ₽)")
    # создаём запрос
    await db.execute(
        "INSERT INTO partner_withdraw_requests (partner_id, amount, status) "
        "VALUES (?, ?, 'pending')",
        (pid, amt), commit=True
    )
    # резервируем в кошельке (debit)
    await db.execute(
        "INSERT INTO partner_wallet_ops (partner_id, type, amount, src) "
        "VALUES (?, 'debit', ?, 'withdraw_pending')",
        (pid, amt), commit=True
    )
    await msg.answer(f"✅ Запрос на {amt:.2f} ₽ создан.")
    await state.clear()
    return await partner_wallet_menu(msg)

@router.callback_query(F.data == "partner_wallet_history")
async def partner_wallet_history(cq: types.CallbackQuery):
    await cq.answer()
    pid = await db.get_partner_id_by_telegram(cq.from_user.id)
    rows = await db.execute(
        "SELECT amount, type, src, created_at "
        "FROM partner_wallet_ops WHERE partner_id=? "
        "ORDER BY created_at DESC LIMIT 10",
        (pid,), fetchall=True
    )
    if not rows:
        return await cq.message.answer("📭 Нет операций.")
    txt = "📜 <b>Операции:</b>\n\n"
    for amt, typ, src, dt in rows:
        sign = "➕" if typ=="credit" else "➖"
        txt += f"{sign}{amt:.2f}₽ — {typ} ({src}) {dt}\n"
    await cq.message.answer(txt, parse_mode="HTML")
