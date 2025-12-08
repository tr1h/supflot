# core/schema.py
# -*- coding: utf-8 -*-
import logging
from core.database import Database

logger = logging.getLogger(__name__)

async def init_db(db: Database):
    """
    Инициализация БД: создаём таблицы, обновляем схему и создаём индексы.
    Не дропаем старые данные!
    """
    logger.info("📦 Initializing DB...")
    # Включаем FK-check для SQLite
    await db.execute("PRAGMA foreign_keys = ON;", commit=False)
    await create_tables(db)
    await patch_schema_if_needed(db)
    await create_indexes(db)
    logger.info("✅ DB initialized successfully.")


async def create_tables(db: Database):
    sql_list = [
        # Партнёры
        """
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_email TEXT,
            telegram_id INTEGER UNIQUE,
            is_active INTEGER DEFAULT 1,
            is_approved INTEGER DEFAULT 0,
            commission_percent REAL DEFAULT 10.0,
            logo TEXT,
            url TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Пользователи
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            is_banned INTEGER DEFAULT 0,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Админы
        """
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            level INTEGER DEFAULT 1 CHECK(level BETWEEN 1 AND 3),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Локации
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            latitude REAL,
            longitude REAL,
            is_active INTEGER DEFAULT 1,
            partner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL
        )
        """,

        # Доски (инвентарь партнёра)
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            total INTEGER NOT NULL CHECK(total > 0),
            quantity INTEGER NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 1000,
            is_active INTEGER DEFAULT 1,
            partner_id INTEGER,
            location_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL,
            FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE SET NULL
        )
        """,

        # Вью для обратной совместимости: partner_boards → boards
        """
        CREATE VIEW IF NOT EXISTS partner_boards AS
        SELECT
            id, name, description, total, quantity, price, is_active,
            partner_id, location_id, created_at
        FROM boards
        """,

        # Изображения досок
        """
        CREATE TABLE IF NOT EXISTS board_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
        )
        """,

        # Бронирования
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            board_id INTEGER NOT NULL,
            board_name TEXT,
            date DATE NOT NULL,
            start_time INTEGER NOT NULL CHECK(start_time BETWEEN 0 AND 23),
            start_minute INTEGER NOT NULL CHECK(start_minute BETWEEN 0 AND 59),
            duration INTEGER NOT NULL CHECK(duration >= 1),
            quantity INTEGER NOT NULL DEFAULT 1,
            amount REAL NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'waiting_partner'
                CHECK(status IN (
                    'waiting_partner','active','canceled','completed',
                    'waiting_card','waiting_cash','waiting_daily'
                )),
            payment_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE RESTRICT
        )
        """,

        # Операции кошелька партнёра
        """
        CREATE TABLE IF NOT EXISTS partner_wallet_ops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('credit','debit')),
            amount REAL NOT NULL,
            src TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE
        )
        """,

        # Суточная аренда (P2P)
        """
        CREATE TABLE IF NOT EXISTS daily_boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            daily_price REAL NOT NULL DEFAULT 1000,
            address TEXT,
            available_quantity INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            partner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE SET NULL
        )
        """,

        # Сотрудники партнёра
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            partner_id INTEGER NOT NULL,
            commission_percent REAL NOT NULL CHECK(commission_percent BETWEEN 0 AND 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE,
            UNIQUE(telegram_id, partner_id)
        )
        """,

        # Выплаты сотрудникам
        """
        CREATE TABLE IF NOT EXISTS employee_wallet_ops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_telegram_id TEXT NOT NULL,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            src TEXT DEFAULT 'booking_commission',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        )
        """,

        # Запросы на вывод средств
        """
        CREATE TABLE IF NOT EXISTS partner_withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(partner_id) REFERENCES partners(id) ON DELETE CASCADE
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # Расходы
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
        """,
    ]

    for sql in sql_list:
        await db.execute(sql, commit=True)


async def patch_schema_if_needed(db: Database):
    # Миграция для старых схем с boards без quantity
    info = await db.execute("PRAGMA table_info(boards);", fetchall=True)
    cols = [r[1] for r in info or []]
    if "quantity" not in cols:
        logger.info("🛠️ Миграция: добавляем колонку boards.quantity")
        await db.execute(
            "ALTER TABLE boards ADD COLUMN quantity INTEGER NOT NULL DEFAULT 0",
            commit=True
        )
        await db.execute(
            "UPDATE boards SET quantity = total",
            commit=True
        )


async def create_indexes(db: Database):
    idx_sql = [
        "CREATE INDEX IF NOT EXISTS idx_partners_tg ON partners(telegram_id)",
        "CREATE INDEX IF NOT EXISTS idx_boards_partner ON boards(partner_id)",
        "CREATE INDEX IF NOT EXISTS idx_boards_location ON boards(location_id)",
        "CREATE INDEX IF NOT EXISTS idx_bookings_board ON bookings(board_id)",
        "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)",
        "CREATE INDEX IF NOT EXISTS idx_wallet_partner ON partner_wallet_ops(partner_id)",
        "CREATE INDEX IF NOT EXISTS idx_employees_partner ON employees(partner_id)",
        "CREATE INDEX IF NOT EXISTS idx_employee_ops_emp ON employee_wallet_ops(employee_telegram_id)"
    ]

    for sql in idx_sql:
        await db.execute(sql, commit=True)
