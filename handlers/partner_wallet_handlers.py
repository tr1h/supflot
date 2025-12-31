"""Обработчики кошелька партнера"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from keyboards.user import get_back_keyboard
from keyboards.common import get_confirm_keyboard

logger = logging.getLogger(__name__)


class WalletStates(StatesGroup):
    """Состояния для работы с кошельком"""
    requesting_withdraw_amount = State()


def register_partner_wallet_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков кошелька партнера"""
    
    @router.callback_query(F.data == "partner:wallet")
    async def partner_wallet(callback: CallbackQuery):
        """Кошелек партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        # Расчет баланса
        wallet_ops = await db.fetchall(
            """SELECT 
                   SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as debits
               FROM partner_wallet_ops 
               WHERE partner_id = ?""",
            (partner['id'],)
        )
        
        credits = wallet_ops[0]['credits'] or 0
        debits = wallet_ops[0]['debits'] or 0
        balance = credits - debits
        
        # Последние операции
        recent_ops = await db.fetchall(
            """SELECT * FROM partner_wallet_ops 
               WHERE partner_id = ? 
               ORDER BY created_at DESC 
               LIMIT 10""",
            (partner['id'],)
        )
        
        # Активные запросы на вывод
        pending_requests = await db.fetchall(
            """SELECT * FROM partner_withdraw_requests 
               WHERE partner_id = ? AND status = 'pending'""",
            (partner['id'],)
        )
        
        text = "💰 <b>Кошелек партнера</b>\n\n"
        text += f"💰 Баланс: <b>{balance:.2f}₽</b>\n"
        text += f"📈 Всего заработано: {credits:.2f}₽\n"
        text += f"📉 Всего выведено: {debits:.2f}₽\n\n"
        
        if pending_requests:
            text += f"⏳ Запросов на вывод: {len(pending_requests)}\n"
            total_pending = sum(req['amount'] for req in pending_requests)
            text += f"Ожидает одобрения: {total_pending:.2f}₽\n\n"
        
        text += "<b>Последние операции:</b>\n"
        for op in recent_ops[:5]:
            icon = "➕" if op['type'] == 'credit' else "➖"
            text += f"{icon} {op['amount']:.2f}₽ - {op.get('src', 'Операция')}\n"
        
        buttons = [
            [InlineKeyboardButton(text="💵 Запросить вывод", callback_data="partner:wallet_withdraw")],
            [InlineKeyboardButton(text="📋 История операций", callback_data="partner:wallet_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partner")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:wallet_withdraw")
    async def partner_wallet_withdraw_start(callback: CallbackQuery, state: FSMContext):
        """Начало запроса на вывод"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            return
        
        # Проверяем баланс
        wallet_ops = await db.fetchall(
            """SELECT 
                   SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as debits
               FROM partner_wallet_ops 
               WHERE partner_id = ?""",
            (partner['id'],)
        )
        balance = (wallet_ops[0]['credits'] or 0) - (wallet_ops[0]['debits'] or 0)
        
        if balance <= 0:
            await callback.message.edit_text(
                "❌ Недостаточно средств на балансе.",
                reply_markup=get_back_keyboard("partner:wallet")
            )
            return
        
        await state.set_state(WalletStates.requesting_withdraw_amount)
        await state.update_data(partner_id=partner['id'], balance=balance)
        
        text = f"💵 <b>Запрос на вывод средств</b>\n\n"
        text += f"Доступно: {balance:.2f}₽\n\n"
        text += "Введите сумму для вывода:"
        
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:wallet"))
    
    @router.message(WalletStates.requesting_withdraw_amount)
    async def partner_wallet_withdraw_amount(message: Message, state: FSMContext):
        """Обработка суммы вывода"""
        try:
            amount = float(message.text.replace(',', '.'))
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число (например, 1000 или 1000.50)")
            return
        
        data = await state.get_data()
        partner_id = data.get('partner_id')
        balance = data.get('balance', 0)
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше нуля.")
            return
        
        if amount > balance:
            await message.answer(f"❌ Недостаточно средств. Доступно: {balance:.2f}₽")
            return
        
        # Проверяем минимальную сумму (например, 100₽)
        if amount < 100:
            await message.answer("❌ Минимальная сумма вывода: 100₽")
            return
        
        try:
            # Создаем запрос на вывод
            await db.execute(
                """INSERT INTO partner_withdraw_requests (partner_id, amount, status)
                   VALUES (?, ?, 'pending')""",
                (partner_id, amount)
            )
            
            text = f"✅ Запрос на вывод {amount:.2f}₽ создан!\n\n"
            text += "Ваш запрос будет рассмотрен администратором в ближайшее время."
            
            await message.answer(text, reply_markup=get_back_keyboard("partner:wallet"))
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error creating withdraw request: {e}")
            await message.answer("❌ Ошибка при создании запроса на вывод.")
    
    @router.callback_query(F.data == "partner:wallet_history")
    async def partner_wallet_history(callback: CallbackQuery):
        """История операций"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            return
        
        # Все операции
        ops = await db.fetchall(
            """SELECT * FROM partner_wallet_ops 
               WHERE partner_id = ? 
               ORDER BY created_at DESC 
               LIMIT 30""",
            (partner['id'],)
        )
        
        if not ops:
            await callback.message.edit_text(
                "📋 История операций пуста.",
                reply_markup=get_back_keyboard("partner:wallet")
            )
            return
        
        text = "📋 <b>История операций</b>\n\n"
        
        for op in ops[:20]:
            icon = "➕" if op['type'] == 'credit' else "➖"
            text += f"{icon} {op['amount']:.2f}₽\n"
            text += f"   {op.get('src', 'Операция')}\n"
            text += f"   {op['created_at']}\n\n"
        
        buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="partner:wallet")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)

