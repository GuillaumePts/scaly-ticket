import uvicorn
import webbrowser
import threading
import time
import sys
import os
from datetime import datetime
from src.config import settings

# --- BOMB TEMPORELLE (DÉSACTIVÉE POUR LE DÉVELOPPEMENT) ---
EXPIRATION_DATE = datetime(2099, 12, 31, 23, 59) # Expiration repoussée en 2099

def check_time_bomb():
    while True:
        if datetime.now() > EXPIRATION_DATE:
            print("\n" + "="*50)
            print(" ⚠️  VERSION D'ÉVALUATION EXPIRÉE  ⚠️")
            print(" La période de test de 4 heures est terminée.")
            print(" Veuillez contacter le développeur pour obtenir la")
            print(" version complète et le contrat de licence.")
            print("="*50 + "\n")
            os._exit(1)
        time.sleep(60) # Vérifie toutes les minutes

if datetime.now() > EXPIRATION_DATE:
    print("\n[ERREUR] Cette version de test a expiré. L'application ne peut pas démarrer.")
    input("Appuyez sur Entrée pour fermer cette fenêtre...")
    sys.exit(1)
# -------------------------------------------------

def open_browser():
    """Attend un peu que le serveur démarre, puis ouvre le navigateur par défaut."""
    time.sleep(1.5)
    print("Ouverture du navigateur web...")
    webbrowser.open(f"http://127.0.0.1:{settings.API_PORT}")

if __name__ == "__main__":
    print(f"--- Lancement de Scaly-Ticket sur http://{settings.API_HOST}:{settings.API_PORT} ---")
    
    # Lancement du thread qui va ouvrir le navigateur
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Lancement du thread de surveillance de l'expiration
    threading.Thread(target=check_time_bomb, daemon=True).start()
    
    # CRITIQUE : Le mode 'reload=True' fait crasher les .exe compilés.
    # Et uvicorn avec une string "src.main:app" ne trouve pas le module dans PyInstaller.
    is_compiled = getattr(sys, 'frozen', False)
    
    import src.main
    try:
        if is_compiled:
            uvicorn.run(src.main.app, host=settings.API_HOST, port=settings.API_PORT, reload=False)
        else:
            uvicorn.run("src.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
    except Exception as e:
        print(f"\n[CRASH CRITIQUE] Le serveur a rencontré une erreur fatale :\n{e}")
        import traceback
        traceback.print_exc()
        
    print("\n[INFO] Le serveur s'est arrêté (ou le port 3000 était déjà utilisé).")
    input("Appuyez sur Entrée pour quitter...")
