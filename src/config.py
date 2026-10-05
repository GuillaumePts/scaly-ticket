import sys
import os
from pathlib import Path
from typing import List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    # Ne pas dépendre du dossier courant pour les chemins de l'application.
    return Path(__file__).resolve().parents[1]


def get_runtime_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


base_path = get_base_path()
runtime_path = get_runtime_path()

class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 3000
    SIMULATION_MODE: bool = False
    
    # We will fetch printers dynamically from DB, no more JSON property here
    # to avoid state mismatch.
    
    model_config = SettingsConfigDict(env_file=str(runtime_path / ".env"), extra="ignore")

settings = Settings()

# Le dossier data doit être persistant et situé à côté de l'EXE
exe_directory = runtime_path
data_path = exe_directory / "data"
data_path.mkdir(exist_ok=True)

db_path = data_path / "scaly_ticket.db"

# Si on est en version compilée et que la DB persistante n'existe pas,
# on copie la DB initiale embarquée dans le MEIPASS vers le dossier persistant.
if getattr(sys, 'frozen', False) and not db_path.exists():
    import shutil
    embedded_db = base_path / "data" / "scaly_ticket.db"
    if embedded_db.exists():
        shutil.copy2(embedded_db, db_path)

# Initialisation de la Base de Données SQLite
from src.database import DatabaseManager

db_path = data_path / "scaly_ticket.db"
db = DatabaseManager(db_path)

# Migration automatique depuis les anciens fichiers JSON (s'ils existent)
old_printers_json = exe_directory / "printers.json"
old_parfums_json = data_path / "parfums_4up.json"
db.migrate_from_json_if_needed(old_printers_json, old_parfums_json)
