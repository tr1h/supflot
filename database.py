import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_NAME = "supclub.db"


async def init_db():
    """Инициализация базы данных с нужной структурой"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Таблица бронирований
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            board_type TEXT NOT NULL,
            date TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            time TEXT NOT NULL,
            start_hour INTEGER NOT NULL,
            end_hour INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Индексы для быстрого поиска
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_user 
        ON bookings(user_id, status)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_datetime 
        ON bookings(date, start_hour, end_hour, status)
        """)

        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Ошибка инициализации БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def save_booking(**kwargs) -> bool:
    """
    Сохраняет бронирование в базу данных
    Требуемые параметры:
    - order_id, user_id, username, full_name
    - board_type, date, time, duration
    - total_price, status (опционально)
    """
    conn = None
    try:
        # Парсим дату и время
        day_str = kwargs['date'].split()[0]  # "DD.MM (День)" -> "DD.MM"
        booking_date = datetime.strptime(day_str, "%d.%m").strftime("%d.%m.%Y")
        day_of_week = kwargs['date'].split()[1][1:-1]  # "DD.MM (День)" -> "День"

        start_hour = int(kwargs['time'].split(":")[0])
        end_hour = start_hour + kwargs['duration']

        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO bookings (
            order_id, user_id, username, full_name, board_type,
            date, day_of_week, time, start_hour, end_hour,
            duration, total_price, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kwargs['order_id'], kwargs['user_id'], kwargs.get('username'),
            kwargs['full_name'], kwargs['board_type'], booking_date,
            day_of_week, kwargs['time'], start_hour, end_hour,
            kwargs['duration'], kwargs['total_price'], kwargs.get('status', 'confirmed')
        ))

        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Ошибка сохранения брони: {e}")
        return False
    finally:
        if conn:
            conn.close()


async def get_booked_slots(date_obj) -> List[Dict]:
    """Возвращает список занятых слотов на указанную дату"""
    conn = None
    try:
        date_str = date_obj.strftime("%d.%m.%Y")
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
        SELECT start_hour, end_hour 
        FROM bookings 
        WHERE date = ? AND status = 'confirmed'
        """, (date_str,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Ошибка получения занятых слотов: {e}")
        return []
    finally:
        if conn:
            conn.close()


async def get_user_bookings(user_id: int) -> List[Dict]:
    """Возвращает активные бронирования пользователя"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 
            order_id, board_type, date, day_of_week, time, 
            duration, total_price, status
        FROM bookings 
        WHERE user_id = ? AND status = 'confirmed'
        ORDER BY date, start_hour
        """, (user_id,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Ошибка получения бронирований пользователя: {e}")
        return []
    finally:
        if conn:
            conn.close()


async def get_booking_by_order_id(order_id: str) -> Optional[Dict]:
    """Возвращает бронирование по его ID"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM bookings WHERE order_id = ?
        """, (order_id,))

        result = cursor.fetchone()
        return dict(result) if result else None
    except sqlite3.Error as e:
        logging.error(f"Ошибка получения брони: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def cancel_booking(order_id: str) -> bool:
    """Отменяет бронирование (мягкое удаление)"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE bookings 
        SET status = 'cancelled' 
        WHERE order_id = ? AND status = 'confirmed'
        """, (order_id,))

        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Ошибка отмены брони: {e}")
        return False
    finally:
        if conn:
            conn.close()


async def get_all_bookings(limit: int = 5) -> List[Dict]:
    """Возвращает последние бронирования (для админа)"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 
            order_id, user_id, username, full_name, 
            board_type, date, time, duration, total_price
        FROM bookings
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Ошибка получения списка бронирований: {e}")
        return []
    finally:
        if conn:
            conn.close()