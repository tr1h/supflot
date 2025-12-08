# core/database.py
# -*- coding: utf-8 -*-
import aiosqlite
import logging
from config import DB_NAME

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_name)
            await self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(
        self, query: str, params: tuple = (),
        *, fetch: bool = False, fetchall: bool = False, commit: bool = True
    ):
        conn = await self.connect()
        cursor = await conn.execute(query, params)

        result = None
        if fetchall:
            result = await cursor.fetchall()
        elif fetch:
            result = await cursor.fetchone()

        if commit:
            await conn.commit()
            if not fetch and not fetchall:
                result = cursor.lastrowid

        await cursor.close()
        return result

    # 🔎 Получить всю информацию о партнёре по telegram_id
    async def get_partner_by_telegram(self, telegram_id: int):
        return await self.execute(
            """
            SELECT id, name, contact_email, telegram_id,
                   is_active, is_approved, commission_percent
            FROM partners
            WHERE telegram_id = ?
            """,
            (telegram_id,),
            fetch=True
        )

    # ➕ Добавить нового партнёра
    async def add_partner(self, name: str, telegram_id: int, contact_email: str | None = None):
        return await self.execute(
            """
            INSERT INTO partners (name, telegram_id, contact_email)
            VALUES (?, ?, ?)
            """,
            (name, telegram_id, contact_email),
            commit=True
        )

    # 🔎 Получить ID партнёра по Telegram ID
    async def get_partner_id_by_telegram(self, telegram_id: int) -> int | None:
        row = await self.execute(
            "SELECT id FROM partners WHERE telegram_id = ?",
            (telegram_id,),
            fetch=True
        )
        return row[0] if row else None

    # ✅ Универсальный метод: получить partner_id (можно вызывать в любом модуле)
    async def get_partner_id(self, telegram_id: int) -> int | None:
        return await self.get_partner_id_by_telegram(telegram_id)

    async def debug_list_pending_completions(db):
        rows = await db.execute(
            "SELECT id, status, amount FROM bookings WHERE status='active' AND date<=date('now')",
            fetchall=True
        )
        print("Pending active bookings:", rows)