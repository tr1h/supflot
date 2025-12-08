# core/crud/partners.py

async def add_partner(db, name: str, contact_email: str, telegram_id: int):
    return await db.execute(
        "INSERT INTO partners(name, contact_email, telegram_id) VALUES (?, ?, ?)",
        (name, contact_email, telegram_id),
        commit=True
    )

async def get_partner_by_telegram(db, telegram_id: int):
    return await db.execute(
        "SELECT * FROM partners WHERE telegram_id=?", (telegram_id,), fetch=True
    )

async def get_unapproved_partners(db):
    return await db.execute("SELECT * FROM partners WHERE is_approved=0", fetchall=True)

async def approve_partner(db, partner_id: int):
    return await db.execute(
        "UPDATE partners SET is_approved=1 WHERE id=?",
        (partner_id,), commit=True
    )
