# miniapp.py - Telegram Mini App для SUPFLOT
from flask import Blueprint, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta

miniapp_bp = Blueprint('miniapp', __name__, url_prefix='/miniapp')
CORS(miniapp_bp)

DB_NAME = os.getenv("DB_NAME", "SupBot.db")

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@miniapp_bp.route('/')
def index():
    """Главная страница Mini App"""
    return render_template('miniapp/index.html')

@miniapp_bp.route('/api/locations')
def api_locations():
    """API для получения локаций"""
    try:
        conn = get_db()
        locations = conn.execute(
            "SELECT id, name, address, latitude, longitude FROM locations WHERE is_active=1"
        ).fetchall()
        conn.close()
        return jsonify([dict(loc) for loc in locations])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@miniapp_bp.route('/api/boards/<int:location_id>')
def api_boards(location_id):
    """API для получения досок по локации"""
    try:
        conn = get_db()
        boards = conn.execute(
            """SELECT id, name, description, price, quantity, total 
               FROM boards WHERE location_id=? AND is_active=1""",
            (location_id,)
        ).fetchall()
        conn.close()
        return jsonify([dict(board) for board in boards])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@miniapp_bp.route('/api/bookings', methods=['POST'])
def api_create_booking():
    """API для создания бронирования"""
    data = request.get_json()
    # Здесь логика создания бронирования
    return jsonify({"success": True, "booking_id": 123})

