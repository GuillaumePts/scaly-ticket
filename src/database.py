import sqlite3
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Assurer que le dossier existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table Printers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS printers (
                    ip TEXT PRIMARY KEY,
                    name TEXT,
                    dpi INTEGER,
                    language TEXT,
                    sector TEXT,
                    port INTEGER,
                    offset_x INTEGER,
                    offset_y INTEGER,
                    offset_x_4up INTEGER,
                    offset_y_4up INTEGER,
                    d_param_4up TEXT,
                    title_size INTEGER,
                    title_bold BOOLEAN,
                    gs1_size INTEGER,
                    gs1_bold BOOLEAN,
                    lot_size INTEGER,
                    lot_bold BOOLEAN
                )
            """)
            
            # Table Parfums
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parfums (
                    id TEXT PRIMARY KEY,
                    nom TEXT,
                    ean13 TEXT
                )
            """)
            conn.commit()

    def migrate_from_json_if_needed(self, printers_json_path: Path, parfums_json_path: Path):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Migrate printers
            cursor.execute("SELECT COUNT(*) as cnt FROM printers")
            if cursor.fetchone()["cnt"] == 0 and printers_json_path.exists():
                logger.info("Migration des imprimantes depuis JSON vers SQLite...")
                try:
                    with open(printers_json_path, "r", encoding="utf-8") as f:
                        printers = json.load(f)
                        for p in printers:
                            cursor.execute("""
                                INSERT INTO printers (
                                    ip, name, dpi, language, sector, port, offset_x, offset_y,
                                    offset_x_4up, offset_y_4up, d_param_4up,
                                    title_size, title_bold, gs1_size, gs1_bold, lot_size, lot_bold
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                p.get("ip"), p.get("name"), p.get("dpi"), p.get("language"), p.get("sector"), p.get("port", 9100),
                                p.get("offset_x", 0), p.get("offset_y", 0),
                                p.get("offset_x_4up"), p.get("offset_y_4up"), p.get("d_param_4up"),
                                p.get("title_size", 0), p.get("title_bold", False),
                                p.get("gs1_size", 0), p.get("gs1_bold", False),
                                p.get("lot_size", 0), p.get("lot_bold", False)
                            ))
                    conn.commit()
                    printers_json_path.rename(printers_json_path.with_suffix('.json.bak'))
                except Exception as e:
                    logger.error(f"Erreur lors de la migration des imprimantes: {e}")

            # Migrate parfums
            cursor.execute("SELECT COUNT(*) as cnt FROM parfums")
            if cursor.fetchone()["cnt"] == 0 and parfums_json_path.exists():
                logger.info("Migration des parfums depuis JSON vers SQLite...")
                try:
                    with open(parfums_json_path, "r", encoding="utf-8") as f:
                        parfums = json.load(f)
                        for p in parfums:
                            cursor.execute("INSERT INTO parfums (id, nom, ean13) VALUES (?, ?, ?)", 
                                         (p.get("id", str(uuid.uuid4())), p.get("nom"), p.get("ean13")))
                    conn.commit()
                    parfums_json_path.rename(parfums_json_path.with_suffix('.json.bak'))
                except Exception as e:
                    logger.error(f"Erreur lors de la migration des parfums: {e}")

    # Printers CRUD
    def get_printers(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM printers")
            return [dict(row) for row in cursor.fetchall()]

    def save_printers(self, printers: List[Dict]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM printers")
            for p in printers:
                cursor.execute("""
                    INSERT INTO printers (
                        ip, name, dpi, language, sector, port, offset_x, offset_y,
                        offset_x_4up, offset_y_4up, d_param_4up,
                        title_size, title_bold, gs1_size, gs1_bold, lot_size, lot_bold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("ip"), p.get("name"), p.get("dpi"), p.get("language"), p.get("sector"), p.get("port", 9100),
                    p.get("offset_x", 0), p.get("offset_y", 0),
                    p.get("offset_x_4up"), p.get("offset_y_4up"), p.get("d_param_4up"),
                    p.get("title_size", 0), p.get("title_bold", False),
                    p.get("gs1_size", 0), p.get("gs1_bold", False),
                    p.get("lot_size", 0), p.get("lot_bold", False)
                ))
            conn.commit()

    def update_printer_offsets(self, ip: str, data: dict) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE printers SET 
                offset_x=?, offset_y=?, title_size=?, title_bold=?,
                gs1_size=?, gs1_bold=?, lot_size=?, lot_bold=?
                WHERE ip=?
            """, (
                data["offset_x"], data["offset_y"], data["title_size"], data["title_bold"],
                data["gs1_size"], data["gs1_bold"], data["lot_size"], data["lot_bold"],
                ip
            ))
            conn.commit()
            return cursor.rowcount > 0

    # Parfums CRUD
    def get_parfums(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM parfums")
            return [dict(row) for row in cursor.fetchall()]

    def get_parfum(self, parfum_id: str) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM parfums WHERE id=?", (parfum_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_parfum(self, nom: str, ean13: str, nom_impression: str = None) -> Dict:
        new_id = str(uuid.uuid4())
        if nom_impression is None:
            nom_impression = nom
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # on handle s'il manque la colonne au cas où
            try:
                cursor.execute("INSERT INTO parfums (id, nom, ean13, nom_impression) VALUES (?, ?, ?, ?)", (new_id, nom, ean13, nom_impression))
            except sqlite3.OperationalError:
                # fallback for older schemas, should not happen since we migrated
                cursor.execute("INSERT INTO parfums (id, nom, ean13) VALUES (?, ?, ?)", (new_id, nom, ean13))
            conn.commit()
        return {"id": new_id, "nom": nom, "ean13": ean13, "nom_impression": nom_impression}

    def update_parfum(self, parfum_id: str, nom: str, ean13: str, nom_impression: str = None) -> bool:
        if nom_impression is None:
            nom_impression = nom
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE parfums SET nom=?, ean13=?, nom_impression=? WHERE id=?", (nom, ean13, nom_impression, parfum_id))
            except sqlite3.OperationalError:
                cursor.execute("UPDATE parfums SET nom=?, ean13=? WHERE id=?", (nom, ean13, parfum_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_parfum(self, parfum_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM parfums WHERE id=?", (parfum_id,))
            conn.commit()
            return cursor.rowcount > 0
