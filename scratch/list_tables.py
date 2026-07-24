import sqlite3
conn = sqlite3.connect('scaly_ticket.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cur.fetchall())
cur.execute("SELECT id, nom, ean13 FROM parfums LIMIT 10")
print("Parfums:", cur.fetchall())
conn.close()
