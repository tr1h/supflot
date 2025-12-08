# core/crud/bookings.py

from datetime import datetime, timedelta

async def add_booking(db, user_id, board_id, date, start_time, start_minute, duration, quantity=1, status='active', payment_method=None):
    row = await db.execute("SELECT price FROM boards WHERE id=?", (board_id,), fetch=True)
    price = row[0] if row else 0
    amount = price * duration * quantity
    return await db.execute(
        """
        INSERT INTO bookings (user_id, board_id, date, start_time, start_minute,
        duration, quantity, amount, status, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, board_id, date, start_time, start_minute,
         duration, quantity, amount, status, payment_method),
        commit=True
    )

async def add_instant_booking(db, user_id, board_id, duration=1, status='active', payment_method=None):
    now = datetime.now()
    if now.minute <= 55:
        start_h, start_m = now.hour, 5
    else:
        nxt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        start_h, start_m = nxt.hour, 5
    date = now.date().isoformat()

    row = await db.execute(
        """
        SELECT b.total - COALESCE(SUM(bk.quantity),0)
        FROM boards b
        LEFT JOIN bookings bk
            ON b.id = bk.board_id
            AND bk.date=? AND bk.start_time=? AND bk.start_minute=? AND bk.status='active'
        WHERE b.id=?
        GROUP BY b.id
        """,
        (date, start_h, start_m, board_id),
        fetch=True
    )
    free = row[0] if row else 0
    if free < 1:
        raise Exception("Нет свободных мест")

    price_row = await db.execute("SELECT price FROM boards WHERE id=?", (board_id,), fetch=True)
    price = price_row[0]
    amount = price * duration

    return await db.execute(
        """
        INSERT INTO bookings
        (user_id, board_id, date, start_time, start_minute,
        duration, quantity, amount, status, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, board_id, date, start_h, start_m,
         duration, 1, amount, status, payment_method),
        commit=True
    )

async def get_bookings_by_user(db, user_id: int):
    return await db.execute(
        """
        SELECT bk.id, b.name, bk.date, bk.start_time, bk.start_minute, bk.duration
        FROM bookings bk
        JOIN boards b ON bk.board_id = b.id
        WHERE bk.user_id=? AND bk.status='active'
        """,
        (user_id,), fetchall=True
    )

async def cancel_booking(db, booking_id: int):
    return await db.execute(
        "UPDATE bookings SET status='canceled' WHERE id=?",
        (booking_id,), commit=True
    )
async def add_daily_booking(user_id, board_id, start_date, duration_days, db):
    end_date = datetime.fromisoformat(start_date) + timedelta(days=duration_days)
    return await db.execute(
        """
        INSERT INTO bookings
        (user_id, board_id, date, start_time, start_minute, duration, quantity, amount, status, payment_method)
        VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (user_id, board_id, start_date, 0, 0, duration_days * 24, 1, 0, 'waiting_daily', None)
    )