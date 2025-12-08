# core/crud/ads.py

async def get_partner_ads(db, partner_id: int):
    return await db.execute(
        """
        SELECT id, title, description,
               price_hourly, price_daily,
               address, available_dates,
               is_active, photo_file_id, created_at
        FROM partner_ads
        WHERE partner_id=?
        ORDER BY created_at DESC
        """,
        (partner_id,), fetchall=True
    )

async def add_partner_ad(db, partner_id, title, description, price_hourly, price_daily, address, available_dates, photo_file_id=None, is_active=True):
    return await db.execute(
        """
        INSERT INTO partner_ads (
            partner_id, title, description,
            price_hourly, price_daily,
            address, available_dates,
            is_active, photo_file_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (partner_id, title, description, price_hourly, price_daily, address, available_dates, int(is_active), photo_file_id),
        commit=True
    )

async def get_ad_by_id(db, ad_id: int):
    return await db.execute(
        """
        SELECT id, partner_id, title, description,
               price_hourly, price_daily,
               address, available_dates,
               is_active, photo_file_id, created_at
        FROM partner_ads
        WHERE id=?
        """,
        (ad_id,), fetch=True
    )

async def update_partner_ad_status(db, ad_id: int, is_active: bool):
    return await db.execute(
        "UPDATE partner_ads SET is_active=? WHERE id=?",
        (int(is_active), ad_id), commit=True
    )

async def update_partner_ad_main_photo(db, ad_id: int, file_id: str):
    return await db.execute(
        "UPDATE partner_ads SET photo_file_id=? WHERE id=?",
        (file_id, ad_id), commit=True
    )

async def add_partner_ad_image(db, ad_id: int, file_id: str):
    return await db.execute(
        "INSERT INTO partner_ad_images(ad_id, file_id) VALUES(?, ?)",
        (ad_id, file_id), commit=True
    )

async def get_partner_ad_images(db, ad_id: int):
    rows = await db.execute(
        "SELECT file_id FROM partner_ad_images WHERE ad_id=?",
        (ad_id,), fetchall=True
    )
    return [r[0] for r in rows] if rows else []
