"""Flask веб-приложение"""
import logging
from flask import Flask, render_template, jsonify, request
from config import Config
from core.database import Database
import asyncio

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY
app.config['DEV_MODE'] = Config.DEV_MODE

# Глобальная переменная для базы данных
db = None
loop = None


def get_db():
    """Получение экземпляра базы данных"""
    global db, loop
    if db is None:
        db = Database()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.connect())
    return db


def run_async(coro):
    """Запуск async функции в синхронном контексте"""
    if loop is None:
        get_db()
    return loop.run_until_complete(coro)


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', dev_mode=app.config['DEV_MODE'])


@app.route('/dev')
def dev_panel():
    """Панель разработчика"""
    if not app.config['DEV_MODE']:
        return jsonify({"error": "Not available in production"}), 403
    return render_template('dev.html')


@app.route('/api/locations')
def api_locations():
    """API: Список активных локаций"""
    database = get_db()
    try:
        locations = run_async(database.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        ))
        return jsonify({"success": True, "data": locations})
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/boards/<int:location_id>')
def api_boards(location_id):
    """API: Доски для локации"""
    database = get_db()
    try:
        boards = run_async(database.fetchall(
            """SELECT * FROM boards 
               WHERE location_id = ? AND is_active = 1 
               ORDER BY name""",
            (location_id,)
        ))
        return jsonify({"success": True, "data": boards})
    except Exception as e:
        logger.error(f"Error fetching boards: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/bookings', methods=['POST'])
def api_create_booking():
    """API: Создание бронирования"""
    database = get_db()
    try:
        data = request.get_json()
        # TODO: Валидация данных
        # TODO: Создание бронирования через BookingService
        return jsonify({"success": True, "message": "Booking created"})
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/webhook', methods=['POST'])
def api_webhook():
    """Webhook для YooKassa"""
    database = get_db()
    try:
        data = request.get_json()
        event = data.get('event')
        
        if event == 'payment.succeeded':
            payment_id = data.get('object', {}).get('id')
            metadata = data.get('object', {}).get('metadata', {})
            booking_id = metadata.get('booking_id')
            
            if booking_id:
                run_async(database.execute(
                    "UPDATE bookings SET status = 'active', payment_id = ? WHERE id = ?",
                    (payment_id, booking_id)
                ))
                logger.info(f"Payment {payment_id} processed for booking {booking_id}")
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/booking/<int:booking_id>')
def api_booking(booking_id):
    """API: Информация о бронировании"""
    database = get_db()
    try:
        booking = run_async(database.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        ))
        if not booking:
            return jsonify({"success": False, "error": "Booking not found"}), 404
        return jsonify({"success": True, "data": booking})
    except Exception as e:
        logger.error(f"Error fetching booking: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/miniapp/')
def miniapp_index():
    """Telegram Mini App главная страница"""
    return render_template('miniapp/index.html')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=Config.DEV_MODE, host='0.0.0.0', port=5000)

