"""Сервис для работы с платежами"""
import logging
import hashlib
import uuid
import base64
import requests
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для работы с платежами"""
    
    @staticmethod
    def generate_payment_id() -> str:
        """Генерация уникального ID платежа"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_idempotence_key() -> str:
        """Генерация ключа идемпотентности для YooKassa"""
        return str(uuid.uuid4())
    
    async def create_yookassa_payment(
        self,
        amount: float,
        description: str,
        booking_id: int,
        return_url: str
    ) -> Optional[Dict[str, Any]]:
        """Создание платежа через YooKassa"""
        if not Config.YK_SHOP_ID or not Config.YK_SECRET:
            logger.error("YooKassa credentials not configured")
            return None
        
        payment_id = self.generate_payment_id()
        idempotence_key = self.generate_idempotence_key()
        
        url = f"{Config.YK_API_URL}/payments"
        headers = {
            "Idempotence-Key": idempotence_key,
            "Content-Type": "application/json"
        }
        
        # Базовая аутентификация
        credentials = f"{Config.YK_SHOP_ID}:{Config.YK_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_credentials}"
        
        payload = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": description,
            "metadata": {
                "booking_id": str(booking_id),
                "payment_id": payment_id
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "pending":
                return {
                    "payment_id": payment_id,
                    "yookassa_id": data.get("id"),
                    "confirmation_url": data.get("confirmation", {}).get("confirmation_url"),
                    "idempotence_key": idempotence_key
                }
            else:
                logger.error(f"YooKassa payment creation failed: {data}")
                return None
        except Exception as e:
            logger.error(f"Error creating YooKassa payment: {e}")
            return None
    
    @staticmethod
    def verify_yookassa_webhook(request_data: Dict[str, Any], secret: str) -> bool:
        """Верификация webhook от YooKassa"""
        # В реальном приложении здесь должна быть проверка подписи
        # Для упрощения пока возвращаем True
        return True
    
    @staticmethod
    def format_amount(amount: float) -> int:
        """Форматирование суммы для Telegram Payments (в копейках)"""
        return int(amount * 100)



