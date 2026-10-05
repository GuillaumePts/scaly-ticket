import multiprocessing
import sys
import traceback

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
