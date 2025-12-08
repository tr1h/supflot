# web_admin.py
from bottle import route, run, template
import sqlite3

DB_PATH = 'SupBot.db'

def get_db():
    return sqlite3.connect(DB_PATH)

@route('/')
def dashboard():
    conn = get_db()
    cur  = conn.cursor()

    # Старая строка — удаляем:
    # revenue = cur.execute("SELECT SUM(amount) FROM payments").fetchone()[0] or 0

    # Новая строка:
    revenue = cur.execute(
        "SELECT SUM(amount) FROM bookings WHERE status='completed'"
    ).fetchone()[0] or 0

    bookings_count = cur.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0] or 0

    conn.close()
    return template('dashboard', revenue=revenue, bookings=bookings_count)

if __name__ == '__main__':
    run(host='localhost', port=8080, debug=True)
