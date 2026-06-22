import sys
import os

# Ajouter le répertoire parent au path pour pouvoir importer depuis src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.zpl_engine import ZPLEngine
from src.printer import PrinterClient
from src.models import TicketData
import time

def main():
    print("Démarrage du test sans découpage (CHUNK_H = 1200)...")
    
    engine = ZPLEngine(dpi=203)
    # On force le découpage à la hauteur totale pour ne pas séparer !
    engine.TOSHIBA_CHUNK_H = 1200 
    
    # Données de test
    data = TicketData(
        Client="FERME DES PEUPLIERS",
        Commande="TEST-001",
        DateLivraison="23/04/26",
        Libelle="6 Yaourt entier Vanille RGF - 2X125G",
        CodeBarre01="13374270043123",
        CodeBarre17="260515",
        CodeBarre10="26L161404",
        Numlot="26L161404",
        Quantite=3
    )
    
    flux = engine.generate_ticket_tpcl(data)
    
    # Remplacer par l'IP de l'imprimante (elle devrait être dans vos logs, par ex 192.168.x.x)
    # Pour ce test local, on peut essayer de l'envoyer.
    # Pour le script, on enregistre d'abord le flux dans un fichier .prn pour vérification
    prn_path = os.path.join(os.path.dirname(__file__), "test_sans_separer.prn")
    with open(prn_path, "wb") as f:
        f.write(flux.encode('latin-1'))
    print(f"Fichier binaire sauvegardé dans {prn_path}")

    # Demander l'IP de l'imprimante
    ip = "200.200.129.200" # Remplacer par l'IP de l'imprimante
    print(f"Envoi à l'imprimante {ip}...")
    try:
        printer = PrinterClient(host=ip)
        printer.send_zpl(flux)
        print("Envoyé avec succès ! Observez si l'imprimante plante (voyant rouge) ou si elle imprime correctement sans coupure.")
    except Exception as e:
        print(f"Erreur d'envoi réseau : {e}")

if __name__ == "__main__":
    main()
