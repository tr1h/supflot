import sqlite3

conn = sqlite3.connect(r'Z:\SupBot\supbot.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    board_id INTEGER,
    date TEXT,
    start_time INTEGER,
    duration INTEGER,
    status TEXT,
    payment_method TEXT
)
''')
conn.commit()
conn.close()
print("Таблица bookings создана!")
