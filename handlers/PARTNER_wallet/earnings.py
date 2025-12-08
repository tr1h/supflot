# handlers/PARTNER_wallet/earnings.py
# -*- coding: utf-8 -*-
"""
Хендлер для кнопки/сообщения "💼 Мой доход":
Подсчитывает и показывает партнёру сумму всех credit‑операций
из таблицы partner_wallet_ops.
"""

from aiogram import Router, types, F

from core.database import Database

# создаём Router и глобальную переменную для БД
earnings_router = Router()
db: Database = None

def register_earnings_handlers(dp: Router, database: Database):
    """
    Регистрирует этот роутер в Dispatcher и сохраняет объект Database.
    Вызывать в run_bot.py после создания dp и db:
        register_earnings_handlers(dp, db)
    """
    global db
    db = database
    dp.include_router(earnings_router)


@earnings_router.message(F.text == "💼 Мой доход")
async def partner_earnings(msg: types.Message):
    """
    Обрабатывает входящее сообщение "💼 Мой доход".
    Суммирует все операции type='credit' для текущего партнёра.
    """
    partner_id = msg.from_user.id

    # Считаем сумму поступлений (credit) из partner_wallet_ops
    row = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
          FROM partner_wallet_ops
         WHERE partner_id = ?
           AND type = 'credit'
        """,
        (partner_id,),
        fetch="one"
    )
    total_earned = row[0] if row else 0.0

    # Отправляем результат пользователю
    await msg.answer(f"💰 Ваш доход: {total_earned:.2f} ₽")
