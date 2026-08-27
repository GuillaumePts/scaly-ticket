import sys
sys.path.insert(0, '.')
from src.config import db

def populate_client_rules():
    # Définition de règles par défaut (ex: SAMADA veut 15 jours min, NORMANDIE 10)
    # On force la création de la table si pas fait
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients_regles (
                nom_client TEXT PRIMARY KEY,
                jours_dlc_min INTEGER NOT NULL
            )
        """)
        conn.commit()
    
    rules = [
        ("SAMADA", 15),
        ("SAMADA GEL MOINS", 15),
        ("NORMANDIE SERVICE FRAIS", 10),
        ("NORMANDIE SERVICE FRAIS SAS", 10)
    ]
    
    updates = 0
    for nom, jours in rules:
        db.save_client_rule(nom, jours)
        updates += 1
        
    print(f"{updates} règles client injectées dans la base de données locale (SQLite).")
    
    all_rules = db.get_all_client_rules()
    for r in all_rules:
        print(f" - {r['nom_client']} : DLC minimum = J+{r['jours_dlc_min']}")

if __name__ == '__main__':
    populate_client_rules()
