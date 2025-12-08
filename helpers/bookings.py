async def finish_booking_and_restore(db: Database, booking_id: int):
    row = await db.execute(
        "SELECT board_id, quantity FROM bookings WHERE id = ? AND status = 'active'",
        (booking_id,), fetch=True
    )
    if not row:
        return False
    board_id, qty = row
    await db.execute(
        "UPDATE boards SET quantity = quantity + ? WHERE id = ?",
        (qty, board_id), commit=True
    )
    await db.execute(
        "UPDATE bookings SET status = 'finished', end_time = datetime('now') WHERE id = ?",
        (booking_id,), commit=True
    )
    return True
