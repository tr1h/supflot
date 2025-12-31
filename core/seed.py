"""Тестовые данные для базы данных"""
import logging
from core.database import Database
from config import Config

logger = logging.getLogger(__name__)


async def seed_db(db: Database):
    """Заполнение базы данных тестовыми данными"""
    logger.info("Seeding database with test data...")
    
    # Добавляем админов
    if Config.ADMIN_IDS:
        for admin_id in Config.ADMIN_IDS:
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO admins (user_id, level) VALUES (?, ?)""",
                    (admin_id, 3)
                )
            except Exception as e:
                logger.warning(f"Could not add admin {admin_id}: {e}")
    
    # Добавляем тестового партнера (если нет админа в ADMIN_IDS, используем первый ID)
    test_partner_tg_id = Config.ADMIN_IDS[0] if Config.ADMIN_IDS else 202140267
    try:
        # Проверяем, есть ли уже партнер
        existing_partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ?",
            (test_partner_tg_id,)
        )
        
        if not existing_partner:
            # Создаем тестового партнера
            await db.execute(
                """INSERT INTO partners (name, contact_email, telegram_id, is_active, is_approved, commission_percent)
                   VALUES (?, ?, ?, 1, 1, 10.0)""",
                ("Тестовый партнер", "test@example.com", test_partner_tg_id)
            )
            # Получаем ID созданного партнера
            partner = await db.fetchone("SELECT id FROM partners WHERE telegram_id = ?", (test_partner_tg_id,))
            partner_id = partner['id']
            logger.info(f"Created test partner with id {partner_id}")
        else:
            partner_id = existing_partner['id']
            # Обновляем статус на одобренный
            await db.execute(
                "UPDATE partners SET is_approved = 1, is_active = 1 WHERE id = ?",
                (partner_id,)
            )
            logger.info(f"Updated existing partner {partner_id}")
        
        # Добавляем тестовую локацию
        existing_location = await db.fetchone(
            "SELECT id FROM locations WHERE partner_id = ? LIMIT 1",
            (partner_id,)
        )
        
        if not existing_location:
            await db.execute(
                """INSERT INTO locations (name, address, latitude, longitude, is_active, partner_id)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                ("Пляж Центральный", "г. Москва, ул. Пляжная, 1", 55.7558, 37.6173, partner_id)
            )
            # Получаем ID созданной локации
            location = await db.fetchone("SELECT id FROM locations WHERE partner_id = ? ORDER BY id DESC LIMIT 1", (partner_id,))
            location_id = location['id']
            logger.info(f"Created test location with id {location_id}")
        else:
            location_id = existing_location['id']
        
        # Добавляем тестовые доски
        existing_boards = await db.fetchone(
            "SELECT COUNT(*) as count FROM boards WHERE partner_id = ?",
            (partner_id,)
        )
        
        if existing_boards['count'] == 0:
            boards = [
                ("SUP доска Classic", "Классическая SUP доска для начинающих. Отлично подходит для спокойной воды.", 500.0, 5, 5, location_id, partner_id),
                ("SUP доска Touring", "Профессиональная доска для длительных прогулок. Стабильная и быстрая.", 800.0, 3, 3, location_id, partner_id),
                ("SUP доска All-Round", "Универсальная доска для всех уровней подготовки. Идеальный баланс стабильности и скорости.", 600.0, 4, 4, location_id, partner_id),
            ]
            
            for board in boards:
                await db.execute(
                    """INSERT INTO boards (name, description, price, total, quantity, location_id, partner_id, is_active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    board
                )
            logger.info(f"Created {len(boards)} test boards")
        
    except Exception as e:
        logger.error(f"Error creating test partner data: {e}")
    
    # Добавляем настройки по умолчанию
    settings = [
        ("platform_commission_percent", str(Config.PLATFORM_COMMISSION_PERCENT)),
        ("work_hours_start", str(Config.WORK_HOURS_START)),
        ("work_hours_end", str(Config.WORK_HOURS_END)),
    ]
    
    for key, value in settings:
        await db.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at) 
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (key, value)
        )
    
    logger.info("Database seeded successfully")

