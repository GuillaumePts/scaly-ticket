import sys
sys.path.insert(0, '.')
import csv
from src.config import db
from src.main import find_ean13_for_libelle

def import_gtin14_from_txt():
    # S'assurer que la BDD est à jour avec la colonne gtin14
    from pathlib import Path
    db.migrate_from_json_if_needed(Path('printers.json'), Path('parfums.json'))
    
    files = [
        'static/img/commandeTest/etiquettebase.txt',
        'static/img/commandeTest/normandie.txt'
    ]
    
    parfums_list = db.get_parfums()
    updates = 0
    not_found = []

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                libelle = row.get('Libelle', '').strip()
                gtin14 = row.get('CodeBarre01', '').strip()
                
                if not libelle or not gtin14:
                    continue
                    
                # Utiliser notre algorithme de scoring pour trouver le parfum correspondant
                nom_match, ean13 = find_ean13_for_libelle(libelle, parfums_list)
                
                if nom_match:
                    # Trouver l'ID du parfum dans la bdd locale
                    target_id = None
                    for p in parfums_list:
                        if p['nom'] == nom_match:
                            target_id = p['id']
                            break
                            
                    if target_id:
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE parfums SET gtin14=? WHERE id=?", (gtin14, target_id))
                            if cursor.rowcount > 0:
                                updates += 1
                else:
                    if libelle not in not_found:
                        not_found.append(libelle)

    print(f"Mise à jour réussie : {updates} GTIN-14 ajoutés ou mis à jour dans la table parfums.")
    if not_found:
        print("Les libellés suivants n'ont pas trouvé de correspondance dans la base locale (il faudra les ajouter manuellement) :")
        for nf in not_found:
            print(f" - {nf}")

if __name__ == '__main__':
    import_gtin14_from_txt()
