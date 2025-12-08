# core/crud/admins.py

async def get_admins(db, level: int = 3):
    return await db.execute(
        "SELECT user_id FROM admins WHERE level=?",
        (level,), fetchall=True
    )
