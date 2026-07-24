import sqlite3

conn = sqlite3.connect('data/scaly_ticket.db')
cur = conn.cursor()

# Afficher tous les parfums RGF
cur.execute("SELECT id, nom, ean13 FROM parfums WHERE nom LIKE '%RGF%'")
rows = cur.fetchall()
print("Avant:")
for r in rows:
    print(" ", r)

# Correction Fraise RGF : bon libellé + bon EAN
cur.execute(
    "UPDATE parfums SET nom='Yaourt fraise 2x125gr RGF', ean13='3374270041221' WHERE nom LIKE '%Fraise%' AND nom LIKE '%RGF%'"
)
conn.commit()

cur.execute("SELECT id, nom, ean13 FROM parfums WHERE nom LIKE '%RGF%'")
print("Après:")
for r in cur.fetchall():
    print(" ", r)

conn.close()
