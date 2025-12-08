import asyncio
from datetime import datetime
from typing import List, Dict
from core.database import Database
from core.partners import PartnerClient, LocalClient

class BookingService:
    def __init__(self, db: Database, partners: List[PartnerClient]):
        self.db = db
        self.partners = partners

    async def get_availability(
        self, start: datetime, end: datetime, resource_type: str
    ) -> List[Dict]:
        # 1) локальные
        local = await LocalClient(self.db).fetch_availability(start, end, resource_type)
        # 2) внешние
        tasks = [p.fetch_availability(start, end, resource_type) for p in self.partners]
        externals = await asyncio.gather(*tasks, return_exceptions=False)
        # 3) объединяем
        result = local.copy()
        for ext in externals:
            result.extend(ext)
        # можно тут отфильтровать по уникальности ID с суффиксом partner
        return result

    async def book(
        self, user_id: int, resource_id: int,
        start: datetime, end: datetime, total_price: float
    ):
        booking_id = await self.db.execute(
            '''INSERT INTO bookings
               (user_id,resource_id,start_time,end_time,total_price)
               VALUES(?,?,?,?,?)''',
            (user_id, resource_id, start.isoformat(), end.isoformat(), total_price),
            commit=True)
        return booking_id
