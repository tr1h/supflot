#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для безопасной очистки проекта SUPFLOT
Удаляет мусорные файлы, старые скрипты и временные данные
"""

import os
import shutil
from pathlib import Path

# Файлы и папки для удаления
FILES_TO_DELETE = [
    # Мусорные файлы
    "=",
    "cd",
    "conn.cursor()",
    "bot.log",
    "supbot.sqbpro",
    
    # Старые скрипты
    "test.py",
    "create_table.py",
    "update_order_status.py",
    "web_admin.py",
    
    # Старый main.py (используется run_bot.py)
    "main.py",
    
    # Старый database.py в корне (используется core/database.py)
    "database.py",
]

DIRS_TO_DELETE = [
    # Старый веб-проект (если не используется)
    # "webapp",  # Раскомментировать, если уверены
]

# Базы данных (уже в .gitignore, но можно удалить локально)
DB_FILES = [
    "SupBot.db",
    "SupBot.db-shm",
    "SupBot.db-wal",
    "core/supbot.db",
    "core/sup_ultimate.db",
    "supclub.db",
    "your_db.sqlite3",
    "orders_site/db.sqlite",
]

def delete_file(filepath):
    """Безопасное удаление файла"""
    path = Path(filepath)
    if path.exists():
        try:
            if path.is_file():
                path.unlink()
                print(f"✅ Удален файл: {filepath}")
                return True
            elif path.is_dir():
                shutil.rmtree(path)
                print(f"✅ Удалена папка: {filepath}")
                return True
        except Exception as e:
            print(f"❌ Ошибка при удалении {filepath}: {e}")
            return False
    else:
        print(f"⚠️  Файл не найден: {filepath}")
        return False

def main():
    print("🧹 Начинаем очистку проекта SUPFLOT...\n")
    
    deleted_count = 0
    
    # Удаляем файлы
    print("📝 Удаление мусорных и старых файлов...")
    for filepath in FILES_TO_DELETE:
        if delete_file(filepath):
            deleted_count += 1
    
    # Удаляем папки
    print("\n📁 Удаление старых папок...")
    for dirpath in DIRS_TO_DELETE:
        if delete_file(dirpath):
            deleted_count += 1
    
    # Удаляем базы данных (опционально)
    print("\n🗄️  Удаление локальных баз данных...")
    print("⚠️  Внимание: базы данных уже в .gitignore, но можно удалить локально")
    response = input("Удалить локальные базы данных? (y/n): ").strip().lower()
    
    if response == 'y':
        for db_file in DB_FILES:
            if delete_file(db_file):
                deleted_count += 1
    else:
        print("⏭️  Пропущено удаление баз данных")
    
    # Исправление файла с ошибкой в имени
    print("\n🔧 Исправление файлов с ошибками в именах...")
    bad_file = Path("orders_site/auth/views.py .py")
    if bad_file.exists():
        new_file = Path("orders_site/auth/views.py")
        try:
            bad_file.rename(new_file)
            print(f"✅ Переименован: views.py .py → views.py")
        except Exception as e:
            print(f"❌ Ошибка при переименовании: {e}")
    
    print(f"\n✨ Очистка завершена! Удалено: {deleted_count} файлов/папок")
    print("\n📋 Что осталось проверить вручную:")
    print("  - webapp/ - старый Django проект?")
    print("  - handlers/NEW_* - используются в run_bot.py, оставить")
    print("  - database/ - проверить использование")

if __name__ == "__main__":
    main()

