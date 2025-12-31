"""Схема базы данных и миграции"""
import logging
from core.database import Database

logger = logging.getLogger(__name__)


async def init_db(db: Database):
    """Инициализация базы данных"""
    logger.info("Initializing database schema...")
    
    schema_sql = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        phone TEXT,
        is_banned INTEGER DEFAULT 0,
        reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Partners table
    CREATE TABLE IF NOT EXISTS partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_email TEXT,
        telegram_id INTEGER UNIQUE NOT NULL,
        is_active INTEGER DEFAULT 1,
        is_approved INTEGER DEFAULT 0,
        commission_percent REAL DEFAULT 10.0,
        logo TEXT,
        url TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_partners_tg ON partners(telegram_id);

    -- Admins table
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        level INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Locations table
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE
    );

    -- Boards table
    CREATE TABLE IF NOT EXISTS boards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        total INTEGER DEFAULT 1,
        quantity INTEGER DEFAULT 1,
        price REAL NOT NULL,
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        location_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_boards_partner ON boards(partner_id);
    CREATE INDEX IF NOT EXISTS idx_boards_location ON boards(location_id);

    -- Bookings table
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        board_id INTEGER,
        board_name TEXT NOT NULL,
        date DATE NOT NULL,
        start_time INTEGER NOT NULL,
        start_minute INTEGER DEFAULT 0,
        duration INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'waiting_partner',
        payment_method TEXT,
        payment_id TEXT,
        partner_id INTEGER,
        employee_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE SET NULL,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE SET NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_bookings_board ON bookings(board_id);
    CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
    CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);

    -- Partner wallet operations
    CREATE TABLE IF NOT EXISTS partner_wallet_ops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        src TEXT,
        booking_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE,
        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_wallet_partner ON partner_wallet_ops(partner_id);

    -- Daily boards (P2P)
    CREATE TABLE IF NOT EXISTS daily_boards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        daily_price REAL NOT NULL,
        address TEXT NOT NULL,
        available_quantity INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        partner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE
    );

    -- Employees
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        partner_id INTEGER NOT NULL,
        commission_percent REAL DEFAULT 30.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE,
        UNIQUE(telegram_id, partner_id)
    );

    -- Partner withdraw requests
    CREATE TABLE IF NOT EXISTS partner_withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (partner_id) REFERENCES partners(id) ON DELETE CASCADE
    );

    -- Board images
    CREATE TABLE IF NOT EXISTS board_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board_id INTEGER NOT NULL,
        file_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
    );

    -- Settings
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Reviews (optional, для будущего расширения)
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        booking_id INTEGER,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL
    );
    """
    
    await db.execute_script(schema_sql)
    
    # Миграция: добавление поля payment_deadline если его нет
    try:
        await db.execute("ALTER TABLE bookings ADD COLUMN payment_deadline TIMESTAMP")
        logger.info("Added payment_deadline column to bookings table")
    except Exception:
        # Колонка уже существует, это нормально
        pass
    
    # Миграция: добавление поля group_id для мультиброни
    try:
        await db.execute("ALTER TABLE bookings ADD COLUMN group_id INTEGER")
        logger.info("Added group_id column to bookings table")
    except Exception:
        # Колонка уже существует, это нормально
        pass
    
    logger.info("Database schema initialized successfully")

