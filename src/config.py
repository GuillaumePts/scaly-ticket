import json
import sys
import os
from pathlib import Path
from typing import List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

def get_base_path():
    if getattr(sys, 'frozen', False):
        # Si on est dans un EXE PyInstaller
        return Path(sys._MEIPASS)
    return Path(os.getcwd())

class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 3000
    PRINTERS_FILE: str = "printers.json"
    
    @property
    def printers(self) -> List[Dict]:
        # printers.json doit rester à côté de l'EXE (pas dedans)
        exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(os.getcwd())
        path = exe_dir / self.PRINTERS_FILE
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
base_path = get_base_path()

# Le dossier data doit être persistant et situé à côté de l'EXE
exe_directory = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(os.getcwd())
data_path = exe_directory / "data"
