# core/crud/users.py

async def add_user(db, user_id: int, username=None, full_name=None, phone=None):
    return await db.execute(
        "INSERT OR IGNORE INTO users(id, username, full_name, phone) VALUES (?, ?, ?, ?)",
        (user_id, username, full_name, phone),
        commit=True
    )

async def get_user(db, user_id: int):
    return await db.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,), fetch=True
    )
