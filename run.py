import multiprocessing
import sys
import os
import time
import threading
import traceback
import webbrowser

def open_browser(port):
    """Attend un peu que le serveur démarre, puis ouvre le navigateur par défaut."""
    time.sleep(1.8)
    print(f"\n[INFO] Ouverture du navigateur web sur http://127.0.0.1:{port}...")
    try:
        webbrowser.open(f"http://127.0.0.1:{port}")
    except Exception as e:
        print(f"[WARN] Impossible d'ouvrir le navigateur automatiquement : {e}")

if __name__ == "__main__":
    # OBLIGATOIRE sous Windows avec PyInstaller pour éviter le crash/fermeture immédiate
    multiprocessing.freeze_support()

    try:
        from src.config import settings
        import src.main
        import uvicorn

        host = settings.API_HOST
        port = settings.API_PORT

        print("=" * 60)
        print("           SCALY-TICKET - LA FERME DES PEUPLIERS")
        print("=" * 60)
        print(f"[INFO] Initialisation du serveur sur http://{host}:{port} ...")

        # Lancement du thread qui va ouvrir le navigateur
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()

        is_compiled = getattr(sys, 'frozen', False)
        if is_compiled:
            # Uvicorn avec instance d'application directe
            uvicorn.run(src.main.app, host=host, port=port, reload=False, log_level="info")
        else:
            uvicorn.run("src.main:app", host=host, port=port, reload=True)

    except Exception as e:
        print(f"\n" + "!" * 60)
        print(f"[CRASH CRITIQUE] Une erreur fatale est survenue :")
        print(f"{e}")
        print("!" * 60)
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("[INFO] Le serveur s'est arrêté.")
    print("=" * 60)
    input("Appuyez sur la touche Entrée pour fermer cette fenêtre...")

