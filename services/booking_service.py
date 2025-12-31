"""Сервис для работы с бронированиями"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from core.database import Database

logger = logging.getLogger(__name__)


class BookingService:
    """Сервис для работы с бронированиями"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_booking(
        self,
        user_id: int,
        board_id: Optional[int],
        board_name: str,
        booking_date: date,
        start_time: int,
        start_minute: int,
        duration: int,
        quantity: int,
        amount: float,
        payment_method: Optional[str] = None,
        partner_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        status: str = "waiting_partner",
        payment_deadline: Optional[datetime] = None
    ) -> int:
        """Создание бронирования"""
        cursor = await self.db.execute(
            """INSERT INTO bookings 
               (user_id, board_id, board_name, date, start_time, start_minute, 
                duration, quantity, amount, status, payment_method, partner_id, employee_id, payment_deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, board_id, board_name, booking_date, start_time, start_minute,
             duration, quantity, amount, status, payment_method, partner_id, employee_id, payment_deadline)
        )
        return cursor.lastrowid
    
    async def get_booking(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """Получение бронирования по ID"""
        return await self.db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
    
    async def get_user_bookings(
        self,
        user_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получение бронирований пользователя"""
        if status:
            return await self.db.fetchall(
                "SELECT * FROM bookings WHERE user_id = ? AND status = ? ORDER BY date DESC, start_time DESC",
                (user_id, status)
            )
        return await self.db.fetchall(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY date DESC, start_time DESC",
            (user_id,)
        )
    
    async def get_partner_bookings(
        self,
        partner_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Получение бронирований партнера"""
        if status:
            return await self.db.fetchall(
                "SELECT * FROM bookings WHERE partner_id = ? AND status = ? ORDER BY date DESC, start_time DESC",
                (partner_id, status)
            )
        return await self.db.fetchall(
            "SELECT * FROM bookings WHERE partner_id = ? ORDER BY date DESC, start_time DESC",
            (partner_id,)
        )
    
    async def update_booking_status(
        self,
        booking_id: int,
        status: str,
        payment_id: Optional[str] = None
    ) -> bool:
        """Обновление статуса бронирования"""
        try:
            if payment_id:
                await self.db.execute(
                    "UPDATE bookings SET status = ?, payment_id = ? WHERE id = ?",
                    (status, payment_id, booking_id)
                )
            else:
                await self.db.execute(
                    "UPDATE bookings SET status = ? WHERE id = ?",
                    (status, booking_id)
                )
            return True
        except Exception as e:
            logger.error(f"Error updating booking status: {e}")
            return False
    
    async def get_active_bookings_to_complete(self) -> List[Dict[str, Any]]:
        """Получение активных бронирований, которые нужно завершить"""
        now = datetime.now()
        today = now.date()
        current_time = now.hour * 60 + now.minute
        
        # Получаем активные бронирования, где время завершения уже прошло
        bookings = await self.db.fetchall(
            """SELECT * FROM bookings 
               WHERE status = 'active' 
               AND ((date < ?) OR (date = ? AND (start_time * 60 + start_minute + duration) <= ?))
               ORDER BY date, start_time""",
            (today, today, current_time)
        )
        return bookings
    
    async def check_board_availability(
        self,
        board_id: int,
        booking_date: date,
        start_time: int,
        start_minute: int,
        duration: int,
        quantity: int
    ) -> bool:
        """Проверка доступности доски на указанное время"""
        # Получаем информацию о доске
        board = await self.db.fetchone("SELECT quantity FROM boards WHERE id = ?", (board_id,))
        if not board or board['quantity'] < quantity:
            return False
        
        # Проверяем пересечения с существующими бронированиями
        end_time_minutes = start_time * 60 + start_minute + duration
        start_time_minutes = start_time * 60 + start_minute
        
        overlapping = await self.db.fetchall(
            """SELECT SUM(quantity) as total_qty FROM bookings 
               WHERE board_id = ? 
               AND date = ? 
               AND status IN ('waiting_partner', 'active', 'waiting_card', 'waiting_cash')
               AND (
                   (start_time * 60 + start_minute < ? AND (start_time * 60 + start_minute + duration) > ?)
                   OR (start_time * 60 + start_minute < ? AND (start_time * 60 + start_minute + duration) > ?)
                   OR (start_time * 60 + start_minute >= ? AND (start_time * 60 + start_minute + duration) <= ?)
               )""",
            (board_id, booking_date, end_time_minutes, start_time_minutes,
             end_time_minutes, start_time_minutes, start_time_minutes, end_time_minutes)
        )
        
        if overlapping and overlapping[0]['total_qty']:
            booked_quantity = overlapping[0]['total_qty']
            return (board['quantity'] - booked_quantity) >= quantity
        
        return board['quantity'] >= quantity
    
    async def get_available_time_slots(
        self,
        board_id: int,
        booking_date: date,
        duration: int = 60,
        quantity: int = 1,
        current_time_minutes: Optional[int] = None
    ) -> List[tuple]:
        """Получение доступных временных слотов для доски на указанную дату"""
        from config import Config
        
        if current_time_minutes is None:
            now = datetime.now()
            current_time_minutes = now.hour * 60 + now.minute
        
        board = await self.db.fetchone("SELECT quantity FROM boards WHERE id = ?", (board_id,))
        if not board:
            return []
        
        available_slots = []
        start_hour = Config.WORK_HOURS_START
        end_hour = Config.WORK_HOURS_END
        
        # Получаем все занятые слоты
        existing_bookings = await self.db.fetchall(
            """SELECT start_time, start_minute, duration, quantity 
               FROM bookings 
               WHERE board_id = ? 
               AND date = ? 
               AND status IN ('waiting_partner', 'active', 'waiting_card', 'waiting_cash')""",
            (board_id, booking_date)
        )
        
        # Проверяем каждый час в рабочее время
        for hour in range(start_hour, end_hour):
            slot_start_minutes = hour * 60
            
            # Если это сегодня, пропускаем прошедшее время
            if booking_date == date.today() and slot_start_minutes < current_time_minutes:
                continue
            
            # Проверяем, есть ли пересечения с существующими бронированиями
            slot_end_minutes = slot_start_minutes + duration
            is_available = True
            booked_qty = 0
            
            for booking in existing_bookings:
                booking_start = booking['start_time'] * 60 + booking['start_minute']
                booking_end = booking_start + booking['duration']
                booking_qty = booking['quantity']
                
                # Проверяем пересечение
                if not (slot_end_minutes <= booking_start or slot_start_minutes >= booking_end):
                    booked_qty += booking_qty
                    if booked_qty >= board['quantity']:
                        is_available = False
                        break
            
            if is_available and (board['quantity'] - booked_qty) >= quantity:
                available_slots.append((hour, 0))
        
        return available_slots

