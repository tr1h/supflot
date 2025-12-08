# handlers/NEW_utils.py
# -*- coding: utf-8 -*-
"""
Утилиты для бронирований:
- Константы дней/месяцев на русском
- Получение погоды из OpenWeather
- Общие таблицы и транзакции бронирований
- Уведомление партнёров
"""

from __future__ import annotations
from typing import Optional, Set
from datetime import datetime
import logging
import aiohttp
from aiogram import Bot

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Русские дни недели / месяцы
# ──────────────────────────────────────────────
WEEKDAYS_RU_SHORT = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
WEEKDAYS_RU_FULL  = ("Понедельник", "Вторник", "Среда", "Четверг",
                     "Пятница", "Суббота", "Воскресенье")
WEEKDAYS_RU = WEEKDAYS_RU_SHORT  # совместимость со старым кодом

MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
)


def weekday_ru(dt: datetime, full: bool = False) -> str:
    """
    Название дня недели на русском для datetime/date.
    full=True -> полное название, иначе короткое.
    """
    idx = dt.weekday()  # 0=Пн ... 6=Вс
    return (WEEKDAYS_RU_FULL if full else WEEKDAYS_RU_SHORT)[idx]


# ──────────────────────────────────────────────
# Погода (OpenWeather)
# ──────────────────────────────────────────────
async def get_weather(lat: float, lon: float, api_key: Optional[str]) -> str:
    """
    Возвращает строку с погодой.
    Если ключа нет или запрос не удался — возвращает пустую строку.
    """
    if not api_key or lat is None or lon is None:
        return ""

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "ru",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
    except Exception:
        return ""

    temp = round(data.get("main", {}).get("temp", 0))
    feels = round(data.get("main", {}).get("feels_like", 0))
    desc = data.get("weather", [{}])[0].get("description", "")
    wind = data.get("wind", {}).get("speed", 0)

    return f"🌡 {temp}°C (ощущается {feels}°C), {desc}. 💨 {wind} м/с"


# ──────────────────────────────────────────────
# Таблицы и транзакции бронирований
# ──────────────────────────────────────────────
async def ensure_common_tables(db):
    """
    Создаём общую таблицу bookings, если её нет.
    Плюс создаём совместимый VIEW partner_boards -> boards,
    чтобы старые места кода не падали.
    """
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            board_id INTEGER NOT NULL,
            board_name TEXT,
            date DATE NOT NULL,
            start_time INTEGER NOT NULL,
            start_minute INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            amount REAL NOT NULL DEFAULT 0,
            payment_method TEXT,
            status TEXT DEFAULT 'active'
                CHECK(status IN ('waiting_partner','active','canceled','completed',
                                 'waiting_card','waiting_cash','waiting_daily','active'))
        )
        """,
        commit=True
    )

    # Совместимость со старым кодом: partner_boards → boards
    try:
        await db.execute("""
            CREATE VIEW IF NOT EXISTS partner_boards AS
            SELECT id, name, description, total, quantity, price, is_active,
                   partner_id, location_id, created_at
            FROM boards
        """, commit=True)
    except Exception:
        # если вдруг нет boards на момент вызова — не критично
        logger.debug("ensure_common_tables: skip partner_boards view (boards not ready yet)")


async def save_booking_and_decrease(db, user_id: int, data: dict, payment_method: str) -> int:
    """
    Сохраняем бронь в bookings + уменьшаем quantity в boards в одной транзакции.
    Валидируем остаток, чтобы не уйти в минус.
    Возвращает booking_id.
    """
    conn = await db.connect()
    await conn.execute("BEGIN")
    try:
        # проверим остаток
        cur_q = await conn.execute("SELECT quantity, name FROM boards WHERE id = ?", (data["board_id"],))
        row_q = await cur_q.fetchone()
        if not row_q:
            raise RuntimeError("Доска не найдена")
        available, board_name = row_q
        need = int(data.get("quantity", 1))
        if available is None:
            available = 0
        if need <= 0:
            raise RuntimeError("Некорректное количество")
        if available < need:
            raise RuntimeError(f"Недостаточно досок ({available} доступно)")

        cur = await conn.execute(
            """
            INSERT INTO bookings
            (user_id, board_id, board_name, date, start_time, start_minute,
             duration, quantity, amount, payment_method, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                user_id,
                data["board_id"],
                data.get("board_name") or board_name,
                data["date"],
                data["start_time"],
                data["start_minute"],
                data["duration"],
                need,
                data["amount"],
                payment_method
            )
        )
        booking_id = cur.lastrowid

        # уменьшаем остаток
        await conn.execute(
            "UPDATE boards SET quantity = quantity - ? WHERE id = ?",
            (need, data["board_id"])
        )

        await conn.commit()
        return booking_id
    except Exception:
        await conn.rollback()
        raise


async def cancel_booking_and_restore(db, booking_id: int) -> bool:
    """
    Ставит статус canceled у брони и возвращает quantity в boards.
    Возвращает True, если успешно.
    """
    conn = await db.connect()
    await conn.execute("BEGIN")
    try:
        cur = await conn.execute(
            "SELECT board_id, quantity, status FROM bookings WHERE id = ?",
            (booking_id,)
        )
        row = await cur.fetchone()
        if not row:
            await conn.rollback()
            return False
        board_id, qty, status = row
        if status == "canceled":
            await conn.rollback()
            return False

        await conn.execute(
            "UPDATE bookings SET status = 'canceled' WHERE id = ?",
            (booking_id,)
        )
        await conn.execute(
            "UPDATE boards SET quantity = quantity + ? WHERE id = ?",
            (qty, board_id)
        )

        await conn.commit()
        return True
    except Exception:
        await conn.rollback()
        raise


# ──────────────────────────────────────────────
# Уведомление партнёров
# ──────────────────────────────────────────────
async def notify_partner(bot: Bot, db, board_id: int, text: str):
    """
    Уведомляем владельца доски (partners.telegram_id) и всех его сотрудников.
    Основной источник — boards; есть мягкий fallback на partner_boards (VIEW).
    """
    try:
        # 1) пытаемся получить партнёра из boards
        row = await db.execute(
            "SELECT partner_id, name FROM boards WHERE id = ?",
            (board_id,), fetch=True
        )

        # fallback на совместимый VIEW, если по какой-то причине boards не сработал
        if not row:
            row = await db.execute(
                "SELECT partner_id, name FROM partner_boards WHERE id = ?",
                (board_id,), fetch=True
            )

        if not row:
            logger.warning("notify_partner: board %s not found", board_id)
            return

        partner_id, board_name = row
        if not partner_id:
            logger.warning("notify_partner: board %s has no partner_id", board_id)
            return

        recipients: Set[int] = set()

        # 2) партнёр
        prow = await db.execute(
            "SELECT telegram_id, COALESCE(is_active,1) FROM partners WHERE id = ?",
            (partner_id,), fetch=True
        )
        if prow:
            p_tg, p_active = prow
            if p_tg and int(p_active) == 1:
                try:
                    recipients.add(int(p_tg))
                except Exception:
                    logger.warning("notify_partner: bad partner telegram_id=%s", p_tg)

        # 3) сотрудники партнёра
        erows = await db.execute(
            "SELECT telegram_id FROM employees WHERE partner_id = ?",
            (partner_id,), fetchall=True
        )
        for (emp_tg,) in erows or []:
            if emp_tg:
                try:
                    recipients.add(int(emp_tg))
                except Exception:
                    logger.warning("notify_partner: bad employee telegram_id=%s", emp_tg)

        if not recipients:
            logger.info("notify_partner: no recipients for partner_id=%s (board %s)", partner_id, board_id)
            return

        for uid in recipients:
            try:
                await bot.send_message(uid, text)
            except Exception as e:
                logger.warning("notify_partner: send to %s failed: %s", uid, e)

    except Exception:
        logger.exception("notify_partner: unexpected error")
