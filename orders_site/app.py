# app.py
import os
import re
import sqlite3
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import requests

# Загрузка .env
load_dotenv()

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Регистрация Mini App
try:
    from miniapp import miniapp_bp
    if miniapp_bp is not None:
        app.register_blueprint(miniapp_bp)
        logger.info("✅ Mini App зарегистрирован")
    else:
        logger.warning("⚠️ Mini App blueprint is None")
except ImportError as e:
    logger.warning(f"⚠️ Mini App не найден: {e}")
except Exception as e:
    logger.error(f"❌ Ошибка регистрации Mini App: {e}")

# Конфигурация
DB_NAME = os.getenv("DB_NAME", "SupBot.db")
YK_SHOP_ID = os.getenv("YK_SHOP_ID")
YK_SECRET = os.getenv("YK_SECRET")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
WORK_HOURS = (9, 21)
BASE_PRICE = 500  # руб. за час

def format_phone(phone: str) -> str:
    """Приводим телефон к формату +7XXXXXXXXXX (E.164)"""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if len(digits) == 10:
        digits = '7' + digits
    return '+' + digits

def db(query, args=(), one=False, commit=False):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
        lastrowid = cur.lastrowid
        conn.close()
        return lastrowid
    if one:
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def init_db():
    """Инициализация БД + миграции"""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        # 1) Базовая схема
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY,
            location_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            total INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            board_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time INTEGER NOT NULL,
            duration INTEGER NOT NULL DEFAULT 1,
            quantity INTEGER NOT NULL DEFAULT 1,
            amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting_card',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(board_id) REFERENCES boards(id)
        );
        """)
        # 2) Миграции: payment_url, payment_id
        cur.execute("PRAGMA table_info(bookings)")
        existing = {row[1] for row in cur.fetchall()}
        if 'payment_url' not in existing:
            cur.execute("ALTER TABLE bookings ADD COLUMN payment_url TEXT")
        if 'payment_id' not in existing:
            cur.execute("ALTER TABLE bookings ADD COLUMN payment_id TEXT")
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_payment_id
                ON bookings(payment_id)
            """)
        # 3) Тестовые данные
        cur.execute("SELECT COUNT(*) FROM locations")
        if cur.fetchone()[0] == 0:
            locs = [
                (1, "Пляж 'Солнечный'", "ул. Пляжная, 1", 55.7558, 37.6176, 1),
                (2, "Озеро 'Голубое'",     "ул. Озерная, 15", 55.7749, 37.6324, 1),
                (3, "Река 'Быстрая'",      "наб. Речная, 3",   55.7367, 37.6498, 1)
            ]
            cur.executemany(
                "INSERT INTO locations (id, name, address, latitude, longitude, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                locs
            )
            boards = [
                (1, 1, "SUP доска 'Волна'", "Проф. доска для серфинга", 5, 1),
                (2, 1, "SUP доска 'Бриз'",  "Для новичков",           3, 1),
                (3, 2, "SUP доска 'Омега'", "Универсальная",           4, 1),
                (4, 3, "SUP доска 'Тайфун'", "Экстрим",               2, 1)
            ]
            cur.executemany(
                "INSERT INTO boards (id, location_id, name, description, total, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                boards
            )
        conn.commit()

# Запускаем миграции
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/locations")
def get_locations():
    return jsonify(db("SELECT * FROM locations WHERE is_active=1"))

@app.route("/boards/<int:location_id>")
def get_boards(location_id):
    return jsonify(db(
        "SELECT id, name, description, total FROM boards WHERE location_id=? AND is_active=1",
        (location_id,)
    ))

@app.route("/timeslots/<int:board_id>/<date>")
def get_timeslots(board_id, date):
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
        if booking_date < datetime.now().date():
            return jsonify({"error": "Дата в прошлом"}), 400

        board = db("SELECT total FROM boards WHERE id=?", (board_id,), one=True)
        if not board:
            return jsonify({"error": "Доска не найдена"}), 404

        bookings = db(
            "SELECT start_time, duration, quantity FROM bookings "
            "WHERE board_id=? AND date=? AND status!='canceled'",
            (board_id, date)
        )

        slots = []
        for hour in range(WORK_HOURS[0], WORK_HOURS[1]):
            booked = sum(
                b['quantity']
                for b in bookings
                if b['start_time'] <= hour < b['start_time'] + b['duration']
            )
            free = max(board['total'] - booked, 0)
            slots.append({"hour": hour, "free": free, "available": free > 0})
        return jsonify(slots)
    except ValueError:
        return jsonify({"error": "Неверный формат даты"}), 400

@app.route("/weather/<float:lat>/<float:lon>")
def get_weather(lat, lon):
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric", "lang": "ru"},
            timeout=5
        )
        resp.raise_for_status()
        d = resp.json()
        return jsonify({
            "temp": round(d["main"]["temp"]),
            "desc": d["weather"][0]["description"].capitalize(),
            "wind": round(d["wind"]["speed"], 1),
            "icon": d["weather"][0]["icon"]
        })
    except requests.RequestException as e:
        logger.error("Ошибка запроса погоды: %s", e)
        return jsonify({"error": "Ошибка получения данных о погоде"}), 500

@app.route("/bookings", methods=["POST"])
def create_booking():
    data = request.get_json() or {}
    required = ["board_id", "date", "start_time", "duration", "quantity", "full_name", "phone"]
    if any(f not in data for f in required):
        return jsonify({"error": "Недостаточно данных"}), 400

    try:
        board = db("SELECT total FROM boards WHERE id=?", (data['board_id'],), one=True)
        if not board:
            return jsonify({"error": "Доска не найдена"}), 404

        b_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
        if b_date < datetime.now().date():
            return jsonify({"error": "Дата в прошлом"}), 400
        if not (WORK_HOURS[0] <= data['start_time'] < WORK_HOURS[1]):
            return jsonify({"error": "Вне рабочего времени"}), 400

        booked = db(
            "SELECT SUM(quantity) AS tot FROM bookings "
            "WHERE board_id=? AND date=? AND start_time=? AND status!='canceled'",
            (data['board_id'], data['date'], data['start_time']), one=True
        )['tot'] or 0
        available = board['total'] - booked
        if data['quantity'] > available:
            return jsonify({"error": "Недостаточно досок", "available": available}), 400

        user = db("SELECT id FROM users WHERE phone=?", (data['phone'],), one=True)
        user_id = user['id'] if user else db(
            "INSERT INTO users (full_name, phone) VALUES (?, ?)",
            (data['full_name'], data['phone']), commit=True
        )

        unit_price = BASE_PRICE * data['duration']
        amount = unit_price * data['quantity']
        payment_id = str(uuid.uuid4())
        headers = {"Idempotence-Key": payment_id}

        phone_e164 = format_phone(data['phone'])
        receipt = {
            "customer": {"full_name": data['full_name'], "phone": phone_e164},
            "items": [{
                "description": f"Аренда SUP доски {data['date']} {data['start_time']}:00",
                "quantity": str(data['quantity']),
                "amount": {"value": f"{unit_price:.2f}", "currency": "RUB"},
                "vat_code": 1,
                "payment_subject": "service",
                "payment_mode": "full_payment"
            }]
        }

        resp = requests.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(YK_SHOP_ID, YK_SECRET),
            json={
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": f"{request.host_url}success"},
                "capture": True,
                "description": f"Аренда SUP доски {data['date']} {data['start_time']}:00",
                "metadata": {"booking_id": payment_id, "user_id": user_id},
                "receipt": receipt
            },
            headers=headers,
            timeout=10
        )
        if not resp.ok:
            logger.error("YooKassa error %s: %s", resp.status_code, resp.text)
            return jsonify({"error": "Ошибка создания платежа", "details": resp.json()}), 502
        pay_data = resp.json()

        booking_id = db(
            """INSERT INTO bookings
               (user_id, board_id, date, start_time, duration, quantity, amount, status, payment_url, payment_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, data['board_id'], data['date'], data['start_time'],
                data['duration'], data['quantity'], amount,
                'waiting_card', pay_data['confirmation']['confirmation_url'], payment_id
            ),
            commit=True
        )

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "payment_link": pay_data['confirmation']['confirmation_url'],
            "amount": amount
        })
    except Exception:
        logger.exception("Ошибка создания бронирования")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.route("/webhook", methods=["POST"])
def yookassa_webhook():
    payload = request.get_json(force=True)
    event = payload.get("event")
    booking_id_meta = payload.get("object", {}).get("metadata", {}).get("booking_id")
    if event == "payment.succeeded":
        db("UPDATE bookings SET status='completed' WHERE payment_id=?", (booking_id_meta,), commit=True)
    elif event == "payment.canceled":
        db("UPDATE bookings SET status='canceled' WHERE payment_id=?", (booking_id_meta,), commit=True)
    return ("", 200)

@app.route("/booking/<int:booking_id>")
def get_booking(booking_id):
    booking = db(
        """SELECT b.*, u.full_name, u.phone, brd.name AS board_name, loc.name AS location_name
           FROM bookings b
           JOIN users u ON b.user_id=u.id
           JOIN boards brd ON b.board_id=brd.id
           JOIN locations loc ON brd.location_id=loc.id
           WHERE b.id=?""",
        (booking_id,), one=True
    )
    if not booking:
        return jsonify({"error": "Бронирование не найдено"}), 404
    return jsonify(booking)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host=host, port=port, debug=debug)
