import uuid
import hmac
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

# /!\ CETTE CLÉ EST LE CŒUR DE LA SÉCURITÉ.
# Ne la modifiez pas une fois le logiciel déployé, sinon les licences seront illisibles.
SECRET_KEY = b"FermePeupliers_AntiHack_Key_2026_Secure!@#"
LICENCE_FILE = "licence.key"

class LicenceError(Exception):
    pass

def get_machine_id() -> str:
    """Retourne l'adresse MAC de la machine (identifiant unique matériel)."""
    mac_num = uuid.getnode()
    # Formatage de l'adresse MAC en chaîne Hexadécimale classique
    mac_hex = ':'.join(['{:02x}'.format((mac_num >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])
    return mac_hex

def generate_signature(machine_id: str, expiration_date: str) -> str:
    """Génère la signature cryptographique (HMAC-SHA256) indéchiffrable sans la SECRET_KEY."""
    payload = f"{machine_id}|{expiration_date}".encode('utf-8')
    signature = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
    return signature

def check_licence():
    """
    Vérifie la validité de la licence. 
    (Désactivé temporairement pour le développement)
    """
    return True

def get_licence_status() -> dict:
    """Retourne le statut de la licence (Désactivé temporairement)"""
    return {"valid": True, "expiration": "9999-12-31", "machine_id": "DEV-MODE"}
