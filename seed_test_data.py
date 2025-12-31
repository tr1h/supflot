import asyncio
from core.database import Database

async def seed():
    db = Database()

    # 📍 Локация
    loc_id = await db.execute(
        "INSERT INTO locations(name, address, latitude, longitude, is_active) VALUES (?, ?, ?, ?, ?)",
        ("Тестовая пристань", "г. Москва, Причальная 1", 55.76, 37.63, 1)
    )

    # 🤝 Партнёр
    partner_id = await db.execute(
        "INSERT INTO partners(name, contact_email, telegram_id, is_approved, is_active) VALUES (?, ?, ?, ?, ?)",
        ("Test Partner", "partner@test.ru", 111222333, 1, 1)
    )

    # 🛶 Доски
    boards = [
        ("SUP Classic", "Устойчивая доска для новичков", 5, 800),
        ("SUP Sport", "Для продвинутых", 3, 1200),
        ("SUP Family", "Большая доска для двоих", 2, 1500)
    ]
    for name, desc, total, price in boards:
        await db.execute(
            """
            INSERT INTO boards(name, description, total, available, price, is_active, partner_id, location_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, desc, total, total, price, 1, partner_id, loc_id)
        )

    print("✅ Тестовые данные добавлены")

if __name__ == "__main__":
    asyncio.run(seed())
