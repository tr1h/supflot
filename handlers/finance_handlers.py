# handlers/finance_handlers.py
# -*- coding: utf-8 -*-

import logging
from datetime import date
from typing import Optional, Dict, Any, List, Tuple

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)
finance_router = Router()
_db: Any = None

# Тексты кнопок
BTN_FINANCE_OVERALL = "📈 Финансы — вся история"
BTN_TURNOVER_TODAY = "📅 Оборот сегодня"
BTN_TURNOVER_MONTH = "📅 Оборот за месяц"
BTN_ADD_EXPENSE = "➕ Добавить расход"
BTN_BACK = "🔙 Назад"

# Статусы броней, которые считаем
GOOD_STATUSES = ("active", "completed")


class ExpenseFSM(StatesGroup):
    amount = State()
    desc = State()


async def _ensure_expenses_table(db):
    """Создаёт таблицу расходов, если её нет."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
        """,
        commit=True
    )


def _date_filters(
    prefix: str,
    date_from: Optional[str],
    date_to: Optional[str],
    column: str = "date"
) -> Tuple[str, List[Any]]:
    """
    Универсальный фильтр по дате:
      prefix — алиас таблицы, column — имя колонки с датой.
    """
    clauses, params = [], []
    if date_from:
        clauses.append(f"{prefix}.{column} >= ?")
        params.append(date_from)
    if date_to:
        clauses.append(f"{prefix}.{column} <= ?")
        params.append(date_to)
    if not clauses:
        return "", []
    return " AND " + " AND ".join(clauses), params


async def get_finance_stats(
    db,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    # гарантируем таблицу расходов
    await _ensure_expenses_table(db)

    # 1) Доход из броней
    bk_clause, bk_params = _date_filters("b", date_from, date_to, "date")
    placeholders = ",".join("?" for _ in GOOD_STATUSES)
    params = list(GOOD_STATUSES) + bk_params

    row = await db.execute(
        f"""
        SELECT COALESCE(SUM(b.amount),0)
          FROM bookings b
         WHERE b.status IN ({placeholders})
           {bk_clause}
        """,
        tuple(params),
        fetch="one"
    )
    income = float(row[0] or 0.0)

    # 2) Расходы вручную
    exp_clause, exp_params = _date_filters("e", date_from, date_to, "date")
    row = await db.execute(
        f"SELECT COALESCE(SUM(e.amount),0) FROM expenses e WHERE 1=1{exp_clause}",
        tuple(exp_params),
        fetch="one"
    )
    expenses = float(row[0] or 0.0)

    # 3) Выплаты партнёрам (по completed-броням)
    # фильтруем по дате в колонке created_at
    part_clause, part_params = _date_filters("o", date_from, date_to, "created_at")
    row = await db.execute(
        f"""
        SELECT COALESCE(SUM(o.amount),0)
          FROM partner_wallet_ops o
         WHERE o.type = 'credit'
           AND o.src  = 'booking_completed'
           {part_clause}
        """,
        tuple(part_params),
        fetch="one"
    )
    partner_payout = float(row[0] or 0.0)

    # 4) Выплаты сотрудникам
    emp_clause, emp_params = _date_filters("b", date_from, date_to, "date")
    row = await db.execute(
        f"""
        SELECT COALESCE(SUM(e.amount),0)
          FROM employee_wallet_ops e
          JOIN bookings b ON e.booking_id = b.id
         WHERE 1=1
           {emp_clause}
        """,
        tuple(emp_params),
        fetch="one"
    )
    employee_payout = float(row[0] or 0.0)

    # 5) Комиссия площадки = остаток
    platform_commission = income - partner_payout - employee_payout - expenses

    # 6) Процентные доли
    pct = lambda x: (x / income * 100) if income else 0.0
    perc = {
        "partner": pct(partner_payout),
        "employee": pct(employee_payout),
        "expenses": pct(expenses),
        "platform": pct(platform_commission),
    }

    return {
        "income": income,
        "expenses": expenses,
        "partner_payout": partner_payout,
        "employee_payout": employee_payout,
        "platform_commission": platform_commission,
        "perc": perc,
        "period": (date_from, date_to),
    }


def format_finance_stats(stats: Dict[str, Any], title: str = "") -> str:
    df, dt = stats["period"]
    period = ""
    if df and dt:
        period = f"Период: {df} – {dt}\n"
    elif df:
        period = f"С {df}\n"
    elif dt:
        period = f"До {dt}\n"

    inc = stats["income"]
    exp = stats["expenses"]
    pp = stats["partner_payout"]
    ep = stats["employee_payout"]
    pl = stats["platform_commission"]
    pc = stats["perc"]

    lines = [
        f"📊 Финансы {title}".strip(),
        period,
        f"🟢 Выручка:     {inc:.2f} ₽",
        f"🔴 Расходы:     {exp:.2f} ₽ ({pc['expenses']:.1f}%)",
        f"🤝 Партнёрам:   {pp:.2f} ₽ ({pc['partner']:.1f}%)",
        f"👤 Сотрудникам: {ep:.2f} ₽ ({pc['employee']:.1f}%)",
        f"🏗 Площадке:    {pl:.2f} ₽ ({pc['platform']:.1f}%)",
    ]
    return "\n".join(lines)


def register_finance_handlers(dp: Router, db):
    global _db
    _db = db
    dp.include_router(finance_router)

    def kb():
        return types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text=BTN_FINANCE_OVERALL)],
                [
                    types.KeyboardButton(text=BTN_TURNOVER_TODAY),
                    types.KeyboardButton(text=BTN_TURNOVER_MONTH),
                ],
                [types.KeyboardButton(text=BTN_ADD_EXPENSE)],
                [types.KeyboardButton(text=BTN_BACK)],
            ],
            resize_keyboard=True
        )

    @finance_router.message(F.text == BTN_BACK)
    async def back_to_admin(msg: types.Message):
        from handlers.NEW_admin_bundle import send_admin_menu
        await msg.answer("🔙 Возвращаемся в админ-меню", reply_markup=send_admin_menu())

    @finance_router.message(F.text == BTN_FINANCE_OVERALL)
    async def show_all(msg: types.Message):
        stats = await get_finance_stats(_db)
        await msg.answer(format_finance_stats(stats, "за всё время"), reply_markup=kb())

    @finance_router.message(F.text == BTN_TURNOVER_TODAY)
    async def show_today(msg: types.Message):
        today = date.today().isoformat()
        stats = await get_finance_stats(_db, today, today)
        await msg.answer(format_finance_stats(stats, "за сегодня"), reply_markup=kb())

    @finance_router.message(F.text == BTN_TURNOVER_MONTH)
    async def show_month(msg: types.Message):
        today = date.today()
        mstart = today.replace(day=1).isoformat()
        stats = await get_finance_stats(_db, mstart, today.isoformat())
        await msg.answer(format_finance_stats(stats, "за месяц"), reply_markup=kb())

    @finance_router.message(F.text == BTN_ADD_EXPENSE)
    async def start_add_expense(msg: types.Message, state: FSMContext):
        await _ensure_expenses_table(_db)
        await state.set_state(ExpenseFSM.amount)
        await msg.answer("📥 Введите сумму расхода:", reply_markup=types.ReplyKeyboardRemove())

    @finance_router.message(ExpenseFSM.amount)
    async def enter_amount(msg: types.Message, state: FSMContext):
        try:
            v = float(msg.text.replace(",", "."))
            if v <= 0:
                raise ValueError()
        except:
            return await msg.answer("❌ Некорректная сумма, введите ещё раз:")
        await state.update_data(amount=v)
        await state.set_state(ExpenseFSM.desc)
        await msg.answer("📝 Теперь введите описание расхода:")

    @finance_router.message(ExpenseFSM.desc)
    async def enter_desc(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        amt = data["amount"]
        desc = msg.text.strip()
        await _db.execute(
            "INSERT INTO expenses (date, amount, description) "
            "VALUES (date('now'), ?, ?)",
            (amt, desc),
            commit=True
        )
        await msg.answer(f"✅ Расход {amt:.2f} ₽ добавлен («{desc}»)", reply_markup=kb())
        await state.clear()

    @finance_router.message(F.text == BTN_FINANCE_OVERALL)
    async def show_all(msg: types.Message):
        ...

    @finance_router.message(F.text == BTN_TURNOVER_TODAY)
    async def show_today(msg: types.Message):
        ...

    @finance_router.message(F.text == BTN_TURNOVER_MONTH)
    async def show_month(msg: types.Message):
        ...
