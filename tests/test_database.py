# tests/test_database.py
import os
import sqlite3
import pytest
import asyncio
from pathlib import Path

import pytest_asyncio

# Перед импортом Database нужно убедиться,
# что переменная config.DB_NAME указывает на нашу временную БД.
@pytest_asyncio.fixture(autouse=True)
def temp_env_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    # подменяем имя БД в конфиге
    monkeypatch.setenv("DB_NAME", str(db_file))
    # если config.DB_NAME читается на модуле, то:
    import importlib, config
    importlib.reload(config)
    yield
    # по окончании тестов файл сам удалится вместе с tmp_path

@pytest_asyncio.fixture
async def db():
    from core.database import Database
    d = Database()
    # инициализируем таблицы + сиды
    await d.init_db()
    return d

@pytest.mark.asyncio
async def test_seed_data(db):
    # после init_db() в locations и partners должен быть хотя бы 1 ряд
    loc = await db.execute("SELECT COUNT(*) FROM locations", fetch=True)
    part = await db.execute("SELECT COUNT(*) FROM partners", fetch=True)
    assert loc[0] >= 1, "После сидов должно быть хотя бы 1 location"
    assert part[0] >= 1, "После сидов должно быть хотя бы 1 partner"

@pytest.mark.asyncio
async def test_locations_crud(db):
    # CREATE
    new_id = await db.add_location("Тестовая", "Адрес 1", 10.0, 20.0)
    assert isinstance(new_id, int) or new_id is None  # sqlite возвращает None, но строка вставлена

    # READ
    row = await db.get_location(new_id)
    assert row[1] == "Тестовая" and row[2] == "Адрес 1"

    # UPDATE
    await db.update_location(new_id, name="Изменено", is_active=0)
    row2 = await db.get_location(new_id)
    assert row2[1] == "Изменено"
    assert row2[5] == 0  # is_active = False

    # DELETE
    await db.delete_location(new_id)
    row3 = await db.get_location(new_id)
    assert row3 is None

@pytest.mark.asyncio
async def test_partners_crud(db):
    # CREATE
    pid = await db.add_partner("P-test", "+100", 999999)
    # sqlite возвращает None, но реальный INSERT отработал
    part = await db.get_partner_by_telegram(999999)
    assert part is not None and part[1] == "P-test"

@pytest.mark.asyncio
async def test_booking_basic(db):
    # создаём сначала пользователя
    await db.add_user(12345, username="u1", full_name="User One", phone="+700000000")
    user = await db.get_user(12345)
    assert user[0] == 12345

    # создаём доску вручную (чтобы гарантировать существование)
    await db.execute(
        "INSERT INTO boards (name, total, price, is_active) VALUES (?, ?, ?, ?)",
        ("BoardX", 2, 500.0, 1), commit=True
    )
    row = await db.execute("SELECT id FROM boards WHERE name = ?", ("BoardX",), fetch=True)
    board_id = row[0]

    # ADD BOOKING
    booking_id = await db.add_booking(12345, board_id, "2099-01-01", 9, 2)
    # Проверим, что вставилось
    bk = await db.execute("SELECT user_id, board_id, date, start_time, duration FROM bookings WHERE id = ?",
                          (booking_id,), fetch=True)
    assert bk[0] == 12345 and bk[1] == board_id and bk[2] == "2099-01-01"
