import aiosqlite
import asyncio

async def add_column():
    async with aiosqlite.connect('your_db.sqlite3') as db:
        await db.execute('ALTER TABLE partners ADD COLUMN is_approved INTEGER DEFAULT 0;')
        await db.commit()

asyncio.run(add_column())
