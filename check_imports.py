#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка импортов и структуры проекта"""

import sys

errors = []
success = []

def check_import(module_name, item_name=None):
    try:
        module = __import__(module_name, fromlist=[item_name] if item_name else [])
        if item_name:
            getattr(module, item_name)
        success.append(f"✅ {module_name}.{item_name if item_name else ''}")
        return True
    except Exception as e:
        errors.append(f"❌ {module_name}.{item_name if item_name else ''}: {e}")
        return False

print("🔍 Проверка импортов...\n")

# Основные модули
check_import("config", "BOT_TOKEN")
check_import("core.database", "Database")
check_import("core.schema", "init_db")
check_import("core.seed", "seed_dev_data")

# Handlers
check_import("handlers.user_cabinet", "register_user_cabinet")
check_import("handlers.NEW_user_bundle", "register_user_handlers")
check_import("handlers.NEW_payments", "register_payment_handlers")
check_import("handlers.NEW_admin_bundle", "register_all_admin_handlers")
check_import("handlers.partner_fsm_handlers", "register_partner_fsm_handlers")
check_import("handlers.partner_cabinet", "register_partner_cabinet")
check_import("handlers.misc_handlers", "router")

# Роутеры
check_import("handlers.daily_handlers", "daily_router")
check_import("handlers.catalog_handlers", "catalog_router")
check_import("handlers.review_handlers", "review_router")

print("\n✅ Успешные импорты:")
for s in success:
    print(f"  {s}")

if errors:
    print("\n❌ Ошибки импорта:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("\n🎉 Все импорты успешны! Проект готов к запуску.")

