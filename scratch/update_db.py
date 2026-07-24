import sqlite3
conn = sqlite3.connect('data/scaly_ticket.db')
cur = conn.cursor()
cur.execute("UPDATE parfums SET nom='RGF Fraise 2x125gr', ean13='3374270043225' WHERE id='32166051-8321-4083-a5bc-dce950ba3212'")
conn.commit()
conn.close()
