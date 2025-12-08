import sqlite3

def update_order_status(order_id, status):
    conn = sqlite3.connect('Z:/SupBot/supbot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
