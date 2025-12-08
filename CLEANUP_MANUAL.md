# 🧹 Ручная очистка проекта

## ✅ Безопасно удалить (не используются):

### 1. Мусорные файлы
```bash
# В корне проекта
del = cd "conn.cursor()" bot.log supbot.sqbpro
```

### 2. Старые скрипты
```bash
del test.py create_table.py update_order_status.py web_admin.py
del main.py database.py
```

### 3. Локальные базы данных (опционально)
```bash
del SupBot.db SupBot.db-shm SupBot.db-wal
del core\supbot.db core\sup_ultimate.db
del supclub.db your_db.sqlite3
del orders_site\db.sqlite
```

### 4. Исправить файл с ошибкой в имени
```bash
# Переименовать
ren "orders_site\auth\views.py .py" "orders_site\auth\views.py"
```

## ⚠️ Оставить (используются):

- `run_bot.py` - основной файл бота ✅
- `orders_site/` - текущий веб-сайт ✅
- `core/` - ядро системы ✅
- `handlers/NEW_*` - используются в run_bot.py ✅
- `webapp/` - возможно используется, проверить ✅

## 📋 Быстрая команда для PowerShell:

```powershell
# Удалить мусорные файлы
Remove-Item "=", "cd", "conn.cursor()", "bot.log", "supbot.sqbpro" -ErrorAction SilentlyContinue

# Удалить старые скрипты
Remove-Item "test.py", "create_table.py", "update_order_status.py", "web_admin.py" -ErrorAction SilentlyContinue
Remove-Item "main.py", "database.py" -ErrorAction SilentlyContinue

# Исправить файл с пробелом
if (Test-Path "orders_site\auth\views.py .py") {
    Rename-Item "orders_site\auth\views.py .py" "views.py"
    Move-Item "views.py" "orders_site\auth\views.py"
}
```

