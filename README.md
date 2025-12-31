# 🏄 SUPFLOT

Платформа для аренды SUP-досок (Stand-Up Paddleboarding) с Telegram-ботом и веб-сайтом.

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone <repo_url>
cd 2244
```

### 2. Создание виртуального окружения

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

Скопируйте `.env.example` в `.env` и заполните необходимые переменные:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл, указав:
- `BOT_TOKEN` - токен Telegram бота
- `YK_SHOP_ID` и `YK_SECRET` - данные для YooKassa (если используете)
- `ADMIN_IDS` - ID администраторов через запятую
- И другие необходимые параметры

### 5. Инициализация базы данных

```bash
python -c "from core.database import Database; from core.schema import init_db; import asyncio; asyncio.run(init_db(Database()))"
```

### 6. Запуск бота

```bash
python run_bot.py
```

### 7. Запуск веб-приложения (в другом терминале)

```bash
cd orders_site
python app.py
```

## 📁 Структура проекта

```
SupBot/
├── run_bot.py              # Точка входа для бота
├── config.py               # Конфигурация
├── requirements.txt        # Зависимости
├── .env                    # Переменные окружения
│
├── core/                   # Ядро системы
│   ├── database.py         # Класс Database (async SQLite)
│   ├── schema.py           # Инициализация БД
│   └── seed.py             # Тестовые данные
│
├── handlers/               # Обработчики бота
│   ├── user_handlers.py    # Пользовательские функции
│   ├── booking_handlers.py # Бронирования
│   └── payment_handlers.py # Платежи
│
├── keyboards/              # Клавиатуры бота
│   ├── user.py
│   ├── partner.py
│   └── admin.py
│
├── services/               # Сервисы
│   ├── booking_service.py
│   ├── payment_service.py
│   └── weather_service.py
│
└── orders_site/            # Flask веб-приложение
    ├── app.py
    ├── templates/
    └── static/
```

## 🔧 Основные функции

### Пользовательские функции
- 🆕 Новая бронь (обычная, мгновенная, суточная, мультибронь)
- 📋 Мои брони
- 📚 Каталог локаций и досок
- 👤 Профиль пользователя

### Партнерские функции
- 💼 Партнерский кабинет
- 📍 Управление локациями
- 🏄 Управление досками
- 📋 Управление бронированиями
- 💰 Кошелек и вывод средств
- 👥 Управление сотрудниками

### Админские функции
- 🔐 Админ-панель
- 👥 Управление партнерами
- 📍 Управление локациями и досками
- 💰 Финансы и выплаты
- 📢 Уведомления

## 💳 Система платежей

- **Telegram Payments** - оплата через Telegram
- **YooKassa** - оплата банковской картой
- **Перевод на карту** - ручной перевод
- **Наличные** - оплата при получении

## 📝 Команды бота

- `/start` - главное меню
- `/help` - справка
- `/daily` - суточная аренда
- `/partner` - партнерская панель
- `/contacts` - контакты поддержки
- `/offer` - оферта
- `/admin` - админ-панель (только для админов)

## 🌐 API Endpoints

- `GET /api/locations` - список активных локаций
- `GET /api/boards/<location_id>` - доски для локации
- `POST /api/bookings` - создание бронирования
- `GET /api/booking/<booking_id>` - информация о бронировании
- `POST /api/webhook` - webhook для YooKassa

## 📄 Лицензия

MIT

## 👥 Поддержка

По вопросам обращайтесь: support@supflot.ru



