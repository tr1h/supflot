from datetime import datetime
from core.database import Database


async def get_boards_by_partner(db: Database, partner_id: int):
    return await db.execute(
        "SELECT * FROM boards WHERE partner_id=? AND is_active=1",
        (partner_id,), fetchall=True
    )


async def get_boards_by_location(db: Database, location_id: int):
    return await db.execute(
        """
        SELECT b.id, b.name,
               b.total - COALESCE(SUM(CASE WHEN bk.status='active' THEN bk.quantity END),0) AS available
        FROM boards b
        LEFT JOIN bookings bk
            ON b.id = bk.board_id
            AND bk.date = date('now') AND bk.status='active'
        WHERE b.location_id=? AND b.is_active=1
        GROUP BY b.id
        """,
        (location_id,), fetchall=True
    )


async def get_available_boards_for_now(db: Database):
    now = datetime.now()
    hour = now.hour if now.minute <= 55 else (now.hour + 1) % 24
    date = now.date().isoformat()
    return await db.execute(
        """
        SELECT b.id, b.name, b.price,
               b.total - COALESCE(SUM(bk.quantity), 0) AS available
        FROM boards b
        LEFT JOIN bookings bk
            ON b.id = bk.board_id
            AND bk.date = ? AND bk.start_time = ? AND bk.start_minute = ? AND bk.status = 'active'
        WHERE b.is_active = 1
        GROUP BY b.id
        HAVING available > 0
        """,
        (date, hour, 5), fetchall=True
    )


async def add_board_image(db: Database, board_id: int, file_id: str):
    return await db.execute(
        "INSERT INTO board_images(board_id, file_id) VALUES (?, ?)",
        (board_id, file_id), commit=True
    )


async def get_board_images(db: Database, board_id: int):
    rows = await db.execute(
        "SELECT file_id FROM board_images WHERE board_id=?",
        (board_id,), fetchall=True
    )
    return [r[0] for r in rows] if rows else []
