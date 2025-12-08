# core/seed.py
# -*- coding: utf-8 -*-
import datetime as dt
import random
from typing import List, Tuple

from core.database import Database


async def seed_dev_data(db: Database):
    """
    Засеять БД реалистичными данными за последний месяц:
      - 3 партнёра, по 2 локации и по 2–3 доски
      - 4–6 пользователей
      - ЕЖЕДНЕВНЫЕ брони (1–6 в день, в основном 'completed')
      - Начисления партнёрам (partner_wallet_ops, src='seed_booking')
      - Несколько расходов (expenses) раз в несколько дней

    Важно: функция НЕ делает сложных SELECT'ов и НЕ использует fetch-параметры.
    Всё вставляется прямыми INSERT'ами через await db.execute(sql, params).
    """

    random.seed(42)

    today: dt.date = dt.date.today()
    start_date: dt.date = today - dt.timedelta(days=30)  # последние 31 день (включая сегодня)

    # --- базовые сущности ----------------------------------------------------
    # партнёры (id, name, tg)
    partners: List[Tuple[int, str, int]] = [
        (1, "Прокат «Греби тут»", 7_000_001),
        (2, "SUP-Клаб Север",     7_000_002),
        (3, "Южная Волна",        7_000_003),
    ]

    # админ/юзеры для правдоподобия
    admin_tg = 202140267
    users: List[Tuple[int, str, str]] = [
        (202140267, "@admin",  "Главный Админ"),
        (202140268, "@alex",   "Алексей Иванов"),
        (202140269, "@maria",  "Мария Петрова"),
        (202140270, "@oleg",   "Олег Смирнов"),
        (202140271, "@dasha",  "Дарья Соколова"),
        (202140272, "@igor",   "Игорь Власов"),
    ]

    # локации (id, name, address, lat, lon, partner_id)
    locations: List[Tuple[int, str, str, float, float, int]] = [
        (1,  "Центральный причал",   "Москва, Береговая 10", 55.75,  37.61, partners[0][0]),
        (2,  "Причал у моста",       "Москва, Набережная 3", 55.751, 37.60, partners[0][0]),
        (3,  "Залив Север-1",        "СПб, Приморская 12",   59.95,  30.20, partners[1][0]),
        (4,  "Залив Север-2",        "СПб, Морская 7",       59.96,  30.19, partners[1][0]),
        (5,  "Южный пляж",           "Сочи, Приморская 5",   43.58,  39.72, partners[2][0]),
        (6,  "Причал Олимпийский",   "Сочи, Олимпийский 1",  43.60,  39.73, partners[2][0]),
    ]

    # доски (id, name, total, price, partner_id, location_id)
    boards: List[Tuple[int, str, int, float, int, int]] = [
        # партнёр 1
        (1,  "SUP Allround 10'6",                 10, 1000.0, partners[0][0], 1),
        (2,  "SUP Touring 12'6",                   6, 1200.0, partners[0][0], 2),
        # партнёр 2
        (3,  "SUP Allround 10'6 (Север)",          8, 1100.0, partners[1][0], 3),
        (4,  "SUP Big 15' (Север, компания)",      3, 2200.0, partners[1][0], 4),
        # партнёр 3
        (5,  "SUP Allround 10'6 (Юг)",            12,  900.0, partners[2][0], 5),
        (6,  "SUP Touring 12'6 (Юг)",              5, 1300.0, partners[2][0], 6),
    ]

    # комиссия платформы (проценты)
    platform_commission = 10.0

    # --- очистка только сид-данных за период --------------------------------
    # удаляем брони за наш период, чтобы не плодить дубликаты
    await db.execute(
        "DELETE FROM bookings WHERE date >= ? AND date <= ?",
        (start_date.isoformat(), today.isoformat()),
    )
    # удаляем только наши начисления партнёрам
    await db.execute(
        "DELETE FROM partner_wallet_ops WHERE src = 'seed_booking'",
        (),
    )
    # расходы оставляем — если хотите, раскомментируйте:
    # await db.execute("DELETE FROM expenses", ())

    # --- вставка базовых сущностей ------------------------------------------
    # партнёры
    for pid, pname, ptg in partners:
        await db.execute(
            """
            INSERT OR IGNORE INTO partners(id, name, contact_email, telegram_id, is_approved, is_active, commission_percent)
            VALUES(?, ?, ?, ?, 1, 1, 10)
            """,
            (pid, pname, f"partner{pid}@example.com", ptg),
        )

    # админ
    await db.execute(
        "INSERT OR IGNORE INTO admins(user_id, username, level) VALUES(?, ?, 3)",
        (admin_tg, "admin"),
    )

    # пользователи
    for uid, uname, fname in users:
        await db.execute(
            "INSERT OR IGNORE INTO users(id, username, full_name) VALUES(?, ?, ?)",
            (uid, uname, fname),
        )

    # локации
    for lid, lname, addr, lat, lon, pid in locations:
        await db.execute(
            """
            INSERT OR IGNORE INTO locations(id, name, address, latitude, longitude, partner_id, is_active)
            VALUES(?, ?, ?, ?, ?, ?, 1)
            """,
            (lid, lname, addr, lat, lon, pid),
        )

    # доски
    for bid, bname, total, price, pid, lid in boards:
        await db.execute(
            """
            INSERT OR IGNORE INTO boards(id, name, total, quantity, price, partner_id, location_id, is_active)
            VALUES(?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (bid, bname, total, total, price, pid, lid),
        )

    # --- генерация броней на каждый день последнего месяца -------------------
    # чтобы в «финансах» был GMV/доход — делаем большинство completed
    day_count = (today - start_date).days + 1
    user_ids = [u[0] for u in users]

    for i in range(day_count):
        day = start_date + dt.timedelta(days=i)
        # сколько броней в этот день (от 1 до 6)
        per_day = random.randint(1, 6)

        for _ in range(per_day):
            # выбираем доску и её параметры
            bid, bname, total, price, pid, lid = random.choice(boards)
            uid = random.choice(user_ids)
            start_hour = random.randint(8, 19)
            start_minute = random.choice([0, 30])
            duration = random.choice([1, 1, 1, 2, 3])  # чаще 1–2 часа
            qty = random.choice([1, 1, 1, 2])          # чаще по одной
            amount = price * duration * qty

            # распределение статусов (большая доля completed)
            status = random.choices(
                ["completed", "completed", "active", "canceled", "waiting_card"],
                weights=[65, 15, 10, 5, 5],
                k=1,
            )[0]

            # создаём бронь
            await db.execute(
                """
                INSERT INTO bookings(
                    user_id, board_id, board_name,
                    date, start_time, start_minute,
                    duration, quantity, amount,
                    status, payment_method, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed', ?)
                """,
                (
                    uid, bid, bname,
                    day.isoformat(), start_hour, start_minute,
                    duration, qty, amount,
                    status,
                    f"{day.isoformat()} 10:00:00",
                ),
            )

            # если бронь завершена — начисляем долю партнёру
            if status == "completed":
                partner_share = amount * (1.0 - platform_commission / 100.0)
                await db.execute(
                    """
                    INSERT INTO partner_wallet_ops(partner_id, type, amount, src, created_at)
                    VALUES(?, 'credit', ?, 'seed_booking', ?)
                    """,
                    (pid, partner_share, f"{day.isoformat()} 23:00:00"),
                )

    # --- расходы (пару записей каждую неделю) --------------------------------
    # расходы нужны для P&L. если таблицы нет — просто пропустится.
    try:
        for d in range(0, day_count, 3):
            day = start_date + dt.timedelta(days=d)
            amount = round(random.uniform(300, 1500), 2)
            desc = random.choice(["Реклама/продвижение", "Аренда причала", "Сервис и ремонт", "Зарплата персонала"])
            await db.execute(
                "INSERT INTO expenses(date, amount, description) VALUES(?, ?, ?)",
                (day.isoformat(), amount, desc),
            )
    except Exception:
        # на случай, если у вас нет таблицы expenses
        pass

    print("✅ Демо-данные за последний месяц созданы: брони + начисления + расходы.")
