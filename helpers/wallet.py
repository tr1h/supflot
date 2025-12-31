# helpers/wallet.py
# -*- coding: utf-8 -*-

from core.database import Database
from typing import Union

async def get_partner_balance(db: Database, telegram_id: int) -> float:
    """
    Возвращает баланс партнёра по его Telegram ID:
      balance = sum(credit) – sum(debit)
    из таблицы partner_wallet_ops.
    """
    # 1) Находим внутренний partner_id
    row = await db.execute(
        "SELECT id FROM partners WHERE telegram_id = ?",
        (telegram_id,),
        fetch="one"
    )
    if not row:
        # партнёр не найден или не зарегистрирован
        return 0.0
    partner_id = row[0]

    # 2) Считаем сумму всех credit и debit операций
    row = await db.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN type = 'credit' THEN amount END), 0) AS total_credit,
          COALESCE(SUM(CASE WHEN type = 'debit'  THEN amount END), 0) AS total_debit
        FROM partner_wallet_ops
        WHERE partner_id = ?
        """,
        (partner_id,),
        fetch="one"
    )
    total_credit, total_debit = row or (0.0, 0.0)

    # 3) Баланс = кредиты минус дебеты
    return float(total_credit) - float(total_debit)


async def get_employee_balance(db: Database, telegram_id: Union[int, str]) -> float:
    """
    Возвращает накопленную комиссию сотрудника:
      commission = SUM(booking.amount * commission_percent/100)
    для всех завершённых броней партнёра, к которому привязан сотрудник.
    """
    # 1) Проверяем, что у нас есть запись о сотруднике и узнаём partner_id и процент
    row = await db.execute(
        "SELECT partner_id, commission_percent FROM employees WHERE telegram_id = ?",
        (str(telegram_id),),
        fetch="one"
    )
    if not row:
        # не сотрудник
        return 0.0
    partner_id, commission_percent = row

    # 2) Суммируем все 'completed' брони этого партнёра
    #    и считаем долю сотрудника от каждой бронли
    row = await db.execute(
        """
        SELECT
          COALESCE(SUM(b.amount * ? / 100.0), 0)
        FROM bookings AS b
        JOIN boards   AS br ON br.id = b.board_id
        WHERE br.partner_id = ?
          AND b.status = 'completed'
        """,
        (commission_percent, partner_id),
        fetch="one"
    )
    total_commission = row[0] if row else 0.0

    return float(total_commission)
