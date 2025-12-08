import sqlite3
from flask_login import UserMixin

def init_db(db_name):
    # создаём все таблицы (users с полем role, locations, boards, bookings…)

def get_user_by_id(user_id) -> UserMixin:
    row = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    return User(row) if row else None

def find_user_by_phone(phone) -> UserMixin:
    row = query_one("SELECT * FROM users WHERE phone=?", (phone,))
    return User(row) if row else None

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.full_name = row["full_name"]
        self.phone = row["phone"]
        self.role = row["role"]  # "admin"|"partner"|"user"
