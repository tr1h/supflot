"""Сервис для работы с отзывами"""
import logging
from typing import Optional, List, Dict, Any
from core.database import Database

logger = logging.getLogger(__name__)


class ReviewService:
    """Сервис для работы с отзывами"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_review(
        self,
        user_id: int,
        booking_id: Optional[int],
        rating: int,
        comment: Optional[str] = None,
        board_id: Optional[int] = None,
        location_id: Optional[int] = None,
        partner_id: Optional[int] = None
    ) -> int:
        """
        Создание отзыва
        
        Args:
            user_id: ID пользователя
            booking_id: ID бронирования
            rating: Оценка (1-5)
            comment: Текст отзыва
            board_id: ID доски
            location_id: ID локации
            partner_id: ID партнера
        
        Returns:
            ID созданного отзыва
        """
        # Если board_id и location_id не указаны, получаем из бронирования
        if booking_id and (not board_id or not location_id or not partner_id):
            booking = await self.db.fetchone(
                "SELECT board_id, partner_id FROM bookings WHERE id = ?",
                (booking_id,)
            )
            if booking:
                if not board_id and booking.get('board_id'):
                    board = await self.db.fetchone(
                        "SELECT location_id FROM boards WHERE id = ?",
                        (booking['board_id'],)
                    )
                    if board:
                        board_id = booking['board_id']
                        location_id = board['location_id']
                if not partner_id:
                    partner_id = booking.get('partner_id')
        
        # Добавляем дополнительные поля, если их нет в схеме
        # Для совместимости проверяем наличие полей
        cursor = await self.db.execute(
            """INSERT INTO reviews (user_id, booking_id, rating, comment)
               VALUES (?, ?, ?, ?)""",
            (user_id, booking_id, rating, comment)
        )
        
        review_id = cursor.lastrowid
        
        # Обновляем дополнительные поля, если они есть в схеме
        # (это делается для будущего расширения схемы)
        
        logger.info(f"Review {review_id} created by user {user_id} for booking {booking_id}")
        return review_id
    
    async def get_review(self, review_id: int) -> Optional[Dict[str, Any]]:
        """Получение отзыва по ID"""
        return await self.db.fetchone(
            "SELECT * FROM reviews WHERE id = ?",
            (review_id,)
        )
    
    async def get_reviews_by_board(
        self,
        board_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получение отзывов к доске
        
        Args:
            board_id: ID доски
            limit: Максимальное количество отзывов
        
        Returns:
            Список отзывов
        """
        # Получаем отзывы через бронирования этой доски
        reviews = await self.db.fetchall("""
            SELECT r.*, u.full_name, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            JOIN bookings b ON r.booking_id = b.id
            WHERE b.board_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (board_id, limit))
        return reviews
    
    async def get_reviews_by_location(
        self,
        location_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получение отзывов к локации
        
        Args:
            location_id: ID локации
            limit: Максимальное количество отзывов
        
        Returns:
            Список отзывов
        """
        # Получаем отзывы через бронирования досок этой локации
        reviews = await self.db.fetchall("""
            SELECT r.*, u.full_name, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            JOIN bookings b ON r.booking_id = b.id
            JOIN boards brd ON b.board_id = brd.id
            WHERE brd.location_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (location_id, limit))
        return reviews
    
    async def get_reviews_by_partner(
        self,
        partner_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получение отзывов партнера
        
        Args:
            partner_id: ID партнера
            limit: Максимальное количество отзывов
        
        Returns:
            Список отзывов
        """
        reviews = await self.db.fetchall("""
            SELECT r.*, u.full_name, u.username, b.board_name, b.date
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            JOIN bookings b ON r.booking_id = b.id
            WHERE b.partner_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (partner_id, limit))
        return reviews
    
    async def get_user_reviews(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получение отзывов пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество отзывов
        
        Returns:
            Список отзывов
        """
        reviews = await self.db.fetchall("""
            SELECT r.*, b.board_name, b.date
            FROM reviews r
            LEFT JOIN bookings b ON r.booking_id = b.id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return reviews
    
    async def get_average_rating(
        self,
        board_id: Optional[int] = None,
        location_id: Optional[int] = None,
        partner_id: Optional[int] = None
    ) -> Optional[float]:
        """
        Получение средней оценки
        
        Args:
            board_id: ID доски (опционально)
            location_id: ID локации (опционально)
            partner_id: ID партнера (опционально)
        
        Returns:
            Средняя оценка или None если отзывов нет
        """
        if board_id:
            result = await self.db.fetchone("""
                SELECT AVG(r.rating) as avg_rating, COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                WHERE b.board_id = ?
            """, (board_id,))
        elif location_id:
            result = await self.db.fetchone("""
                SELECT AVG(r.rating) as avg_rating, COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                JOIN boards brd ON b.board_id = brd.id
                WHERE brd.location_id = ?
            """, (location_id,))
        elif partner_id:
            result = await self.db.fetchone("""
                SELECT AVG(r.rating) as avg_rating, COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                WHERE b.partner_id = ?
            """, (partner_id,))
        else:
            return None
        
        if result and result.get('count', 0) > 0:
            return round(result['avg_rating'], 2)
        return None
    
    async def get_review_count(
        self,
        board_id: Optional[int] = None,
        location_id: Optional[int] = None,
        partner_id: Optional[int] = None
    ) -> int:
        """
        Получение количества отзывов
        
        Args:
            board_id: ID доски (опционально)
            location_id: ID локации (опционально)
            partner_id: ID партнера (опционально)
        
        Returns:
            Количество отзывов
        """
        if board_id:
            result = await self.db.fetchone("""
                SELECT COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                WHERE b.board_id = ?
            """, (board_id,))
        elif location_id:
            result = await self.db.fetchone("""
                SELECT COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                JOIN boards brd ON b.board_id = brd.id
                WHERE brd.location_id = ?
            """, (location_id,))
        elif partner_id:
            result = await self.db.fetchone("""
                SELECT COUNT(*) as count
                FROM reviews r
                JOIN bookings b ON r.booking_id = b.id
                WHERE b.partner_id = ?
            """, (partner_id,))
        else:
            return 0
        
        return result['count'] if result else 0
    
    async def user_can_review_booking(
        self,
        user_id: int,
        booking_id: int
    ) -> bool:
        """
        Проверка, может ли пользователь оставить отзыв на бронирование
        
        Args:
            user_id: ID пользователя
            booking_id: ID бронирования
        
        Returns:
            True если может, False иначе
        """
        # Проверяем, что бронирование завершено и принадлежит пользователю
        booking = await self.db.fetchone("""
            SELECT status, user_id FROM bookings 
            WHERE id = ? AND user_id = ?
        """, (booking_id, user_id))
        
        if not booking:
            return False
        
        # Проверяем, что бронирование завершено
        if booking['status'] != 'completed':
            return False
        
        # Проверяем, что отзыв еще не оставлен
        existing_review = await self.db.fetchone("""
            SELECT id FROM reviews 
            WHERE user_id = ? AND booking_id = ?
        """, (user_id, booking_id))
        
        return existing_review is None

