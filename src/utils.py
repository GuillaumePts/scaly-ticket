from datetime import datetime, timedelta

def parse_gs1_date(date_str: str) -> datetime:
    """Parse une date au format YYMMDD."""
    return datetime.strptime(date_str, "%y%m%d")

def format_gs1_date(dt: datetime) -> str:
    """Formate une date pour le GS1-128 (YYMMDD)."""
    return dt.strftime("%y%m%d")

def get_days_offset(dlc_str: str) -> int:
    """Calcule le décalage (offset) en jours entre AUJOURD'HUI et la DLC."""
    try:
        dlc_date = parse_gs1_date(dlc_str)
        today = datetime.now()
        # On calcule l'écart en jours
        delta = dlc_date.date() - today.date()
        return delta.days
    except:
        return 0

def get_updated_dlc(days_offset: int) -> str:
    """Génère la DLC au format YYMMDD à l'instant T + offset jours."""
    new_date = datetime.now() + timedelta(days=days_offset)
    return format_gs1_date(new_date)

def get_updated_lot(current_lot: str) -> str:
    """
    Met à jour le numéro de lot lors du passage à minuit.
    Logique à adapter selon le format du client.
    """
    # Exemple : Si le lot finit par un nombre, on l'incrémente
    import re
    match = re.search(r"(\d+)$", current_lot)
    if match:
        number = int(match.group(1))
        prefix = current_lot[:match.start()]
        return f"{prefix}{number + 1}"
    
    # Sinon on ajoute simplement un suffixe ou on laisse tel quel
    return f"{current_lot}_BIS"
