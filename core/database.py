"""Асинхронная обертка для работы с SQLite"""
import aiosqlite
import logging
from typing import Optional, List, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DB_NAME
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(
                self.db_path,
                timeout=30.0
            )
            # Включить поддержку foreign keys
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.commit()
            logger.info(f"Connected to database: {self.db_path}")
    
    async def close(self):
        """Закрытие соединения"""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    async def execute(self, query: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """Выполнение запроса"""
        if self._connection is None:
            await self.connect()
        try:
            cursor = await self._connection.execute(query, parameters)
            await self._connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Database error: {e}, Query: {query}, Params: {parameters}")
            raise
    
    async def executemany(self, query: str, parameters: List[tuple]) -> aiosqlite.Cursor:
        """Выполнение запроса с несколькими параметрами"""
        if self._connection is None:
            await self.connect()
        try:
            cursor = await self._connection.executemany(query, parameters)
            await self._connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Database error: {e}, Query: {query}")
            raise
    
    async def fetchone(self, query: str, parameters: tuple = ()) -> Optional[Dict[str, Any]]:
        """Получение одной записи"""
        if self._connection is None:
            await self.connect()
        try:
            cursor = await self._connection.execute(query, parameters)
            row = await cursor.fetchone()
            if row is None:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        except Exception as e:
            logger.error(f"Database error: {e}, Query: {query}, Params: {parameters}")
            raise
    
    async def fetchall(self, query: str, parameters: tuple = ()) -> List[Dict[str, Any]]:
        """Получение всех записей"""
        if self._connection is None:
            await self.connect()
        try:
            cursor = await self._connection.execute(query, parameters)
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Database error: {e}, Query: {query}, Params: {parameters}")
            raise
    
    async def execute_script(self, script: str):
        """Выполнение SQL скрипта"""
        if self._connection is None:
            await self.connect()
        try:
            await self._connection.executescript(script)
            await self._connection.commit()
        except Exception as e:
            logger.error(f"Database script error: {e}")
            raise



