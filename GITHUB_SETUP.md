# 📦 Инструкция по размещению проекта на GitHub

## 🚀 Быстрый старт

### 1. Создание репозитория на GitHub

1. Зайдите на [GitHub](https://github.com)
2. Нажмите "New repository"
3. Название: `supflot` или `supflot-platform`
4. Описание: "Платформа для аренды сапбордов с партнерской системой"
5. Выберите **Private** (пока проект в разработке)
6. **НЕ** добавляйте README, .gitignore, лицензию (они уже есть)
7. Нажмите "Create repository"

### 2. Инициализация Git в проекте

```bash
# Перейдите в папку проекта
cd D:\SupBot

# Инициализируйте Git
git init

# Добавьте все файлы (кроме тех, что в .gitignore)
git add .

# Создайте первый коммит
git commit -m "Initial commit: SUPFLOT platform"

# Добавьте remote репозиторий (замените YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/supflot.git

# Отправьте код на GitHub
git branch -M main
git push -u origin main
```

### 3. Настройка .env для разных окружений

**Важно:** Файл `.env` уже в `.gitignore`, но нужно создать шаблон:

```bash
# Создайте файл .env.example
cp .env .env.example  # Если .env уже есть
# Или создайте вручную
```

**Содержимое `.env.example`:**

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# База данных
DB_NAME=supbot.db

# Платежи
YK_SHOP_ID=your_yookassa_shop_id
YK_SECRET=your_yookassa_secret
PAYMENTS_PROVIDER_TOKEN=your_telegram_payments_token

# Погода
OPENWEATHER_KEY=your_openweather_api_key

# Администраторы (через запятую)
ADMIN_IDS=202140267,1383730017

# Комиссия платформы (%)
PLATFORM_COMMISSION_PERCENT=10

# Часы работы
WORK_HOURS_START=8
WORK_HOURS_END=22

# Канал отзывов
REVIEW_CHANNEL=@your_review_channel
```

### 4. Настройка GitHub Secrets (для CI/CD)

Если планируете автоматический деплой:

1. Зайдите в Settings → Secrets and variables → Actions
2. Добавьте секреты:
   - `BOT_TOKEN`
   - `YK_SHOP_ID`
   - `YK_SECRET`
   - И другие чувствительные данные

### 5. Создание веток для разработки

```bash
# Создайте ветку для разработки
git checkout -b develop

# Создайте ветку для фичи
git checkout -b feature/new-website

# Вернитесь на main
git checkout main
```

## 📝 Рекомендации по коммитам

### Формат коммитов

Используйте понятные сообщения:

```bash
# Хорошо
git commit -m "Add partner registration flow"
git commit -m "Fix payment webhook handler"
git commit -m "Update website booking form"

# Плохо
git commit -m "fix"
git commit -m "update"
git commit -m "changes"
```

### Структура коммитов

```
<type>: <subject>

<body>

<footer>
```

**Типы:**
- `feat`: новая функция
- `fix`: исправление бага
- `docs`: документация
- `style`: форматирование
- `refactor`: рефакторинг
- `test`: тесты
- `chore`: рутинные задачи

**Примеры:**

```bash
git commit -m "feat: add partner wallet system"
git commit -m "fix: resolve booking time slot conflict"
git commit -m "docs: update README with setup instructions"
```

## 🔒 Безопасность

### Что НЕ должно попасть в Git

- ✅ `.env` файлы
- ✅ Токены и ключи API
- ✅ Базы данных
- ✅ Логи с чувствительными данными
- ✅ Личные данные пользователей

### Проверка перед коммитом

```bash
# Проверьте, что не добавляете чувствительные данные
git status

# Проверьте содержимое файлов перед коммитом
git diff
```

## 📋 GitHub Issues и Projects

### Создание Issues

Используйте шаблоны:

- 🐛 Bug report
- ✨ Feature request
- 📝 Documentation
- 🔧 Improvement

### Labels

- `bug` - ошибка
- `enhancement` - улучшение
- `documentation` - документация
- `help wanted` - нужна помощь
- `good first issue` - для новичков

## 🚀 Деплой

### Варианты деплоя

1. **VPS (Vultr, DigitalOcean, Hetzner)**
   - Установка через SSH
   - PM2 для Node.js процессов
   - Supervisor для Python процессов

2. **Heroku**
   - Простой деплой
   - Ограниченные ресурсы

3. **Docker**
   - Контейнеризация
   - Легкий деплой

4. **Vercel/Netlify** (для фронтенда)
   - Автоматический деплой
   - CDN

### Пример Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run_bot.py"]
```

## 📊 GitHub Actions (CI/CD)

### Пример workflow

Создайте `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/
```

## 🔗 Полезные ссылки

- [GitHub Docs](https://docs.github.com)
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## ✅ Чеклист перед первым push

- [ ] `.gitignore` настроен
- [ ] `.env` не в репозитории
- [ ] Чувствительные данные удалены из кода
- [ ] README.md обновлен
- [ ] Лицензия добавлена (если нужно)
- [ ] Первый коммит создан
- [ ] Remote репозиторий добавлен
- [ ] Код отправлен на GitHub

## 🎯 Следующие шаги

1. ✅ Проект на GitHub
2. Настройка CI/CD
3. Создание Issues для задач
4. Настройка деплоя
5. Приглашение команды (если есть)

