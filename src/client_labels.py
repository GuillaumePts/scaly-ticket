"""Profils de libellés Ligne 1. Toutes les écritures restent dans SQLite."""
import re
import math
import sqlite3
import unicodedata
import uuid
from datetime import date, datetime, timedelta

DEFAULT_TEMPLATE = "${description}"
CATEGORIES = ["ENTIER", "GELIFIE", "PARAFFINÉ", "BRASSE", "MAIGRE", "DESSERT", "FF"]
VARIABLES = {"parfum", "description", "description_2", "categorie", "unite", "client", "quantite", "poids"}
TOKEN = re.compile(r"\$\{([^{}]+)\}")
SCHEMA = """
CREATE TABLE IF NOT EXISTS ligne1_clients (
    id TEXT PRIMARY KEY, scope TEXT NOT NULL, customer_id TEXT NOT NULL DEFAULT '',
    customer_number TEXT NOT NULL DEFAULT '', display_name TEXT NOT NULL,
    name_key TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ligne1_customer_id
    ON ligne1_clients(scope, customer_id) WHERE customer_id <> '';
CREATE UNIQUE INDEX IF NOT EXISTS ligne1_customer_number
    ON ligne1_clients(scope, customer_number) WHERE customer_number <> '';
CREATE UNIQUE INDEX IF NOT EXISTS ligne1_customer_name
    ON ligne1_clients(scope, name_key) WHERE customer_id = '' AND customer_number = '';
CREATE TABLE IF NOT EXISTS ligne1_rules (
    client_id TEXT NOT NULL REFERENCES ligne1_clients(id), category TEXT NOT NULL,
    template_300 TEXT NOT NULL DEFAULT '${description}',
    template_203 TEXT NOT NULL DEFAULT '${description}', enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (client_id, category)
);
CREATE TABLE IF NOT EXISTS ligne1_blocked_categories (
    client_id TEXT NOT NULL REFERENCES ligne1_clients(id), category TEXT NOT NULL,
    PRIMARY KEY (client_id, category)
);
CREATE TABLE IF NOT EXISTS ligne1_client_filter_days (
    client_id TEXT PRIMARY KEY REFERENCES ligne1_clients(id), min_dlc_days INTEGER NOT NULL CHECK(min_dlc_days >= 0)
);
CREATE TABLE IF NOT EXISTS ligne1_flavours (
    scope TEXT NOT NULL, item_no TEXT NOT NULL, flavour TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, item_no)
);
"""


class ProfileConflict(ValueError):
    pass


def normalized(value):
    return " ".join(str(value or "").strip().casefold().split())


def make_scope(config):
    # Inclure le tenant protège aussi les installations qui changent de client BC.
    return "|".join(normalized(config.get(key)) for key in ("BC_TENANT_ID", "BC_ENVIRONMENT", "BC_COMPANY"))


def category_key(value):
    # Conserver la forme de BC et reconnaître l'ancienne faute sans créer de doublon.
    category = str(value or "").strip().upper()
    return "PARAFFINÉ" if category == "PARRAFINE" else category


def customer_id(value):
    value = str(value or "").strip().lower()
    return "" if value == "00000000-0000-0000-0000-000000000000" else value


def validate_min_dlc_days(value, required=False):
    if value is None or value == "":
        if required:
            raise ValueError("Le nombre minimum de jours avant DLC est obligatoire pour créer le profil client.")
        return None
    if isinstance(value, bool):
        raise ValueError("Le nombre minimum de jours doit être un entier positif ou nul.")
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Le nombre minimum de jours doit être un entier positif ou nul.") from exc
    if str(value).strip() not in (str(days), f"+{days}") or days < 0:
        raise ValueError("Le nombre minimum de jours doit être un entier positif ou nul.")
    return days


def _parse_calendar_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value.split("T")[0], pattern).date()
        except ValueError:
            continue
    return None


def _fifo_lot_candidates(item, min_days):
    delivery_date = _parse_calendar_date(item.get("DateLivraison"))
    all_lots = item.get("available_lots") or []
    minimum_dlc = delivery_date + timedelta(days=min_days) if delivery_date is not None and min_days is not None else None
    if minimum_dlc is None:
        if item.get("LotManualOverride") and item.get("LotManuallySelected"):
            selected_number = str(item.get("Numlot") or "").strip()
            selected = next((lot for lot in all_lots
                             if str(lot.get("lot") or "").strip() == selected_number
                             and float(lot.get("qty") or 0) > 0), None)
            return ([selected] if selected else []), None
        return [], None
    eligible = []
    for lot in all_lots:
        if lot.get("blocked"):
            continue
        try:
            if float(lot.get("qty") or 0) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        expiry = _parse_calendar_date(lot.get("expiration_date") or lot.get("dlc_display"))
        if expiry is None:
            # Anciennes données : le code GS1 est au format YYMMDD.
            code = str(lot.get("code_barre_17") or "")
            if re.fullmatch(r"\d{6}", code):
                try:
                    expiry = datetime.strptime(code, "%y%m%d").date()
                except ValueError:
                    expiry = None
        if expiry is None or expiry < minimum_dlc:
            continue
        eligible.append((
            str(lot.get("posting_date") or "9999-12-31"),
            expiry,
            str(lot.get("lot") or ""),
            lot,
        ))
    eligible.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    ordered = [entry[3] for entry in eligible]
    selected_number = str(item.get("Numlot") or "").strip()
    if item.get("LotManuallySelected") and selected_number:
        selected = next((lot for lot in all_lots
                         if str(lot.get("lot") or "").strip() == selected_number
                         and float(lot.get("qty") or 0) > 0), None)
        if selected and item.get("LotManualOverride"):
            ordered = [selected] + [lot for lot in ordered if lot is not selected]
        elif selected and any(lot is selected for lot in ordered):
            ordered = [selected] + [lot for lot in ordered if lot is not selected]
    return ordered, minimum_dlc


def _pots_per_sales_unit(unit_code):
    unit = re.sub(r"\s+", "", str(unit_code or "").upper())
    if unit in {"POT", "POTS", "UNITE", "UNIT", "U"}:
        return 1
    match = re.fullmatch(r"X(\d+)(?:\+(\d+)G?)?", unit)
    if match:
        return int(match.group(1)) + int(match.group(2) or 0)
    return None


def _pots_per_carton(item_category):
    category = unicodedata.normalize("NFKD", str(item_category or "").upper())
    category = "".join(char for char in category if not unicodedata.combining(char))
    category = re.sub(r"[^A-Z0-9]+", "", category)
    if category in {"BRASSE", "FF"}:
        return 6
    if category in {"PARAFFINE", "PARRAFINE"}:
        return 24
    if category in {"ENTIER", "NATURE", "MAIGRE", "GELIFIE", "DESSERT"}:
        return 12
    return None


def _allocate_bc_order_line(item, min_days, lot_reservations=None):
    factor = _pots_per_sales_unit(item.get("UnitOfMeasureCode"))
    supplied_factor = item.get("BCPotsPerSalesUnit") or item.get("qtyPerUnitOfMeasure")
    if supplied_factor not in (None, ""):
        try:
            parsed_factor = int(float(supplied_factor))
            if parsed_factor > 0:
                factor = parsed_factor
        except (TypeError, ValueError):
            pass
    try:
        requested_units = max(0, int(item.get("BCRequestedQuantity", item.get("Quantite", 0)) or 0))
    except (TypeError, ValueError):
        requested_units = 0
    supplied_base_quantity = item.get("BCRequestedBasePots")
    try:
        requested_pots = max(0, int(math.ceil(float(supplied_base_quantity)))) if supplied_base_quantity not in (None, "") else requested_units * factor if factor else 0
    except (TypeError, ValueError):
        requested_pots = requested_units * factor if factor else 0
    if supplied_base_quantity not in (None, "") and factor:
        requested_units = math.ceil(requested_pots / factor)
    carton_pots = _pots_per_carton(item.get("ItemCategoryCode"))
    lot_reservations = lot_reservations if lot_reservations is not None else {}
    reservation_prefix = (str(item.get("Item_No") or ""),)
    available_lots = []
    for lot in item.get("available_lots") or []:
        lot_copy = dict(lot)
        reservation_key = reservation_prefix + (str(lot.get("lot") or ""),)
        try:
            lot_copy["qty"] = max(0, float(lot.get("qty") or 0) - lot_reservations.get(reservation_key, 0))
        except (TypeError, ValueError):
            lot_copy["qty"] = 0
        available_lots.append(lot_copy)
    selection_item = dict(item)
    selection_item["available_lots"] = available_lots
    lots, minimum_dlc = _fifo_lot_candidates(selection_item, min_days)
    base = dict(item)
    base["ClientMinimumDlcDate"] = minimum_dlc.isoformat() if minimum_dlc else None
    base["BCOrderAllocated"] = True
    base["BCRequestedQuantity"] = requested_units
    base["BCRequestedPots"] = requested_pots
    base["BCPotsPerSalesUnit"] = factor
    base["CartonPotsPerCase"] = carton_pots
    base["LotSelectionWarning"] = ""
    base["LotShortageWarning"] = ""
    base["CartonLabelWarning"] = "" if carton_pots else f"Type d’article « {item.get('ItemCategoryCode') or 'inconnu'} » : nombre de pots par carton à configurer avant l’impression 300 dpi."
    base["QuantiteEtiquettes203"] = 0
    base["CartonLabelBlocked"] = not carton_pots

    if not factor:
        base.update({"Quantite": 0, "QuantiteCartons": 0, "QuantitePots": 0,
                     "Numlot": "", "CodeBarre10": "", "CodeBarre17": "",
                     "LotSelectionBlocked": True,
                     "LotSelectionWarning": f"Unité de vente « {item.get('UnitOfMeasureCode') or 'inconnue'} » non reconnue : allocation du stock impossible."})
        return [base]

    remaining_units = requested_units
    allocated = []
    for lot in lots:
        try:
            available_pots = max(0, int(float(lot.get("qty") or 0)))
        except (TypeError, ValueError):
            continue
        lot_units = min(remaining_units, available_pots // factor)
        if lot_units <= 0:
            continue
        pots = lot_units * factor
        row = dict(base)
        lot_number = str(lot.get("lot") or "")
        carton_labels = math.ceil(pots / carton_pots) if carton_pots else 0
        row.update({
            "Numlot": lot_number,
            "CodeBarre10": lot_number,
            "CodeBarre17": lot.get("code_barre_17", ""),
            "Quantite": carton_labels,
            "QuantiteCartons": carton_labels,
            "QuantitePots": pots,
            "QuantiteEtiquettes203": lot_units,
            "LotAllocatedPotQuantity": pots,
            "LotAllocatedSalesUnits": lot_units,
            "LotSelectionBlocked": False,
            "CartonLabelBlocked": not carton_pots,
            "LotManuallySelected": bool(item.get("LotManuallySelected") and lot_number == str(item.get("Numlot") or "")),
            "LotManualOverride": bool(item.get("LotManualOverride") and lot_number == str(item.get("Numlot") or "")),
        })
        allocated.append(row)
        reservation_key = reservation_prefix + (str(lot.get("lot") or ""),)
        lot_reservations[reservation_key] = lot_reservations.get(reservation_key, 0) + pots
        remaining_units -= lot_units
        if remaining_units <= 0:
            break

    remaining_pots = remaining_units * factor
    if allocated:
        if remaining_pots:
            allocated[0]["LotShortageWarning"] = (
                f"Stock insuffisant : {remaining_pots} pot(s) manquant(s) pour « {item.get('Libelle') or item.get('Item_No') or 'ce produit'} ». "
                f"La quantité imprimable est limitée au stock disponible."
            )
        return allocated

    if min_days is None:
        warning = "Le délai minimum avant DLC du client doit être renseigné."
    elif minimum_dlc is None:
        warning = "La date de livraison est absente ou invalide."
    elif remaining_pots:
        warning = f"Aucun lot FIFO disponible en quantité suffisante pour cette unité de vente (besoin : {remaining_pots} pots minimum)."
    else:
        warning = f"Aucun lot qualité non bloqué avec une DLC au {minimum_dlc.strftime('%d/%m/%Y')} ou après."
    base.update({"Quantite": 0, "QuantiteCartons": 0, "QuantitePots": 0,
                 "Numlot": "", "CodeBarre10": "", "CodeBarre17": "",
                 "LotSelectionBlocked": True, "LotSelectionWarning": warning})
    return [base]


def validate_template(value):
    value = str(value)
    if not value.strip() or len(value) > 500 or any(ord(c) < 32 for c in value):
        raise ValueError("Le modèle doit contenir entre 1 et 500 caractères sur une seule ligne.")
    unknown = set(TOKEN.findall(value)) - VARIABLES
    if unknown:
        raise ValueError("Variable inconnue : " + ", ".join(sorted(unknown)))
    if "${" in TOKEN.sub("", value):
        raise ValueError("Variable incomplète : utilisez ${nom_variable}.")
    return value


def propose_flavour(description):
    """Proposition prudente ; jamais utilisée pour sélectionner un code-barres."""
    text = unicodedata.normalize("NFD", description or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    flavours = ["vanille", "abricot", "fraise", "framboise", "myrtille", "nature", "citron",
                "amande", "chocolat", "caramel", "cafe", "figue", "poire", "cerise",
                "noisette", "miel", "peche", "marron", "mandarine", "griotte", "litchi"]
    found = [f for f in flavours if re.search(r"\b" + re.escape(f) + r"\b", text)]
    return " / ".join("Café" if f == "cafe" else f.capitalize() for f in found)


def template_context(item):
    return {
        "parfum": item.get("Parfum", ""),
        "description": item.get("ItemDescription") or item.get("Libelle", ""),
        "description_2": item.get("ItemDescription2", ""),
        "categorie": item.get("ItemCategoryCode", ""),
        "unite": item.get("UnitOfMeasureCode", ""),
        "client": item.get("Client", ""),
        "quantite": item.get("QuantiteCartons", item.get("Quantite", "")),
        "poids": item.get("ItemWeightGrams", ""),
    }


def render_template(template, item):
    validate_template(template)
    context = template_context(item)
    missing = sorted({key for key in TOKEN.findall(template) if context.get(key) in (None, "")})
    label = TOKEN.sub(lambda m: str(context.get(m.group(1)) if context.get(m.group(1)) is not None else ""), template)
    # Ne pas laisser d'espaces multiples après substitution d'une valeur absente.
    return " ".join(label.split()), [f"Valeur absente : ${{{key}}}" for key in missing]


class ClientLabelStore:
    def __init__(self, db, scope):
        self.db = db
        self.scope = scope

    def _get(self, conn, profile_id):
        row = conn.execute("SELECT * FROM ligne1_clients WHERE id=? AND scope=?", (profile_id, self.scope)).fetchone()
        if row is None:
            raise ValueError("Profil client introuvable dans cette société et cet environnement.")
        result = dict(row)
        rules = [dict(r) for r in conn.execute(
            "SELECT category,template_300,template_203,enabled FROM ligne1_rules WHERE client_id=? ORDER BY category", (profile_id,))]
        canonical_rules = {}
        for rule in rules:
            category = category_key(rule["category"])
            if category not in canonical_rules or rule["category"] == category:
                rule["category"] = category
                canonical_rules[category] = rule
        result["rules"] = list(canonical_rules.values())
        result["blocked_categories"] = sorted({category_key(r["category"]) for r in conn.execute(
            "SELECT category FROM ligne1_blocked_categories WHERE client_id=?", (profile_id,))})
        days_row = conn.execute("SELECT min_dlc_days FROM ligne1_client_filter_days WHERE client_id=?", (profile_id,)).fetchone()
        result["min_dlc_days"] = days_row["min_dlc_days"] if days_row else None
        return result

    def get(self, profile_id):
        with self.db.get_connection() as conn:
            return self._get(conn, profile_id)

    def list(self):
        with self.db.get_connection() as conn:
            return [self._get(conn, r["id"]) for r in conn.execute(
                "SELECT id FROM ligne1_clients WHERE scope=? ORDER BY display_name", (self.scope,)).fetchall()]

    def delete(self, profile_id, revision):
        """Supprime un profil et ses réglages dans SQLite, sans toucher aux données BC."""
        with self.db.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            profile = conn.execute(
                "SELECT revision FROM ligne1_clients WHERE id=? AND scope=?",
                (profile_id, self.scope),
            ).fetchone()
            if profile is None:
                raise ValueError("Profil client introuvable dans cette société et cet environnement.")
            if profile["revision"] != revision:
                raise ProfileConflict("Ce profil a été modifié par un autre opérateur. Rechargez-le avant de le supprimer.")
            conn.execute("DELETE FROM ligne1_rules WHERE client_id=?", (profile_id,))
            conn.execute("DELETE FROM ligne1_blocked_categories WHERE client_id=?", (profile_id,))
            conn.execute("DELETE FROM ligne1_client_filter_days WHERE client_id=?", (profile_id,))
            conn.execute("DELETE FROM ligne1_clients WHERE id=? AND scope=?", (profile_id, self.scope))
        return {"deleted": True}

    def find(self, identity):
        identifier = customer_id(identity.get("CustomerId"))
        number = str(identity.get("CustomerNumber") or "").strip()
        name = normalized(identity.get("Client"))
        with self.db.get_connection() as conn:
            for column, value in (("customer_id", identifier), ("customer_number", number)):
                if value:
                    row = conn.execute(f"SELECT id FROM ligne1_clients WHERE scope=? AND {column}=?", (self.scope, value)).fetchone()
                    if row:
                        return self._get(conn, row["id"])
            # Ne jamais raccrocher deux clients portant le même nom mais des IDs distincts.
            row = conn.execute("""SELECT id FROM ligne1_clients WHERE scope=? AND name_key=?
                AND customer_id='' AND customer_number=''""", (self.scope, name)).fetchone()
            return self._get(conn, row["id"]) if row else None

    def create(self, identity, categories=(), rules=(), active=True, blocked_categories=(), min_dlc_days=None):
        name = str(identity.get("Client") or "").strip()
        if not name or len(name) > 200:
            raise ValueError("Le nom du client est obligatoire (200 caractères maximum).")
        min_dlc_days = validate_min_dlc_days(min_dlc_days, required=True)
        supplied = {}
        for rule in rules:
            category = category_key(rule.get("category"))
            if not category or category in supplied:
                raise ValueError("Chaque catégorie doit avoir un code non vide et unique.")
            validate_template(rule["template_300"])
            validate_template(rule["template_203"])
            supplied[category] = rule
        profile_id = str(uuid.uuid4())
        with self.db.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("""INSERT INTO ligne1_clients(id,scope,customer_id,customer_number,display_name,name_key,active)
                    VALUES(?,?,?,?,?,?,?)""", (profile_id, self.scope, customer_id(identity.get("CustomerId")),
                    str(identity.get("CustomerNumber") or "").strip(), name, normalized(name), int(active)))
            except sqlite3.IntegrityError as exc:
                raise ProfileConflict("Ce client possède déjà un profil. Rechargez la liste.") from exc
            conn.execute("INSERT INTO ligne1_client_filter_days(client_id,min_dlc_days) VALUES(?,?)", (profile_id, min_dlc_days))
            for category in sorted(set(CATEGORIES + list(supplied) + [category_key(c) for c in categories if category_key(c)])):
                rule = supplied.get(category, {})
                conn.execute("INSERT INTO ligne1_rules(client_id,category,template_300,template_203,enabled) VALUES(?,?,?,?,?)",
                             (profile_id, category, rule.get("template_300", DEFAULT_TEMPLATE),
                              rule.get("template_203", DEFAULT_TEMPLATE), int(rule.get("enabled", True))))
            for category in sorted({category_key(c) for c in blocked_categories if category_key(c)}):
                conn.execute("INSERT INTO ligne1_blocked_categories(client_id,category) VALUES(?,?)", (profile_id, category))
            return self._get(conn, profile_id)

    def save(self, profile_id, revision, name, active, rules, identity=None, flavour=None, blocked_categories=None, min_dlc_days=None):
        name = str(name).strip()
        if not name or len(name) > 200:
            raise ValueError("Le nom du client est obligatoire (200 caractères maximum).")
        categories = set()
        for rule in rules:
            category = category_key(rule.get("category"))
            if not category or category in categories:
                raise ValueError("Chaque catégorie doit avoir un code non vide et unique.")
            categories.add(category)
            validate_template(rule["template_300"])
            validate_template(rule["template_203"])
        with self.db.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = self._get(conn, profile_id)
            if current["revision"] != revision:
                raise ProfileConflict("Ce profil a été modifié par un autre opérateur. Fermez et rechargez le profil.")
            identifier = current["customer_id"]
            customer_number = current["customer_number"]
            if identity:
                identifier = customer_id(identity.get("CustomerId") or identifier)
                customer_number = str(identity.get("CustomerNumber") or customer_number).strip()
            try:
                conn.execute("""UPDATE ligne1_clients SET display_name=?,name_key=?,active=?,customer_id=?,customer_number=?,
                    revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND scope=?""",
                    (name, normalized(name), int(active), identifier, customer_number, profile_id, self.scope))
            except sqlite3.IntegrityError as exc:
                raise ProfileConflict("Cet identifiant appartient déjà à un autre profil.") from exc
            # L'API enregistre la liste complète, sans supprimer de catégories silencieusement.
            for rule in rules:
                conn.execute("""INSERT INTO ligne1_rules(client_id,category,template_300,template_203,enabled) VALUES(?,?,?,?,?)
                    ON CONFLICT(client_id,category) DO UPDATE SET template_300=excluded.template_300,
                    template_203=excluded.template_203,enabled=excluded.enabled""",
                    (profile_id, category_key(rule["category"]), rule["template_300"], rule["template_203"], int(rule.get("enabled", True))))
            if min_dlc_days is not None:
                min_dlc_days = validate_min_dlc_days(min_dlc_days, required=True)
                conn.execute("""INSERT INTO ligne1_client_filter_days(client_id,min_dlc_days) VALUES(?,?)
                    ON CONFLICT(client_id) DO UPDATE SET min_dlc_days=excluded.min_dlc_days""", (profile_id, min_dlc_days))
            if blocked_categories is not None:
                conn.execute("DELETE FROM ligne1_blocked_categories WHERE client_id=?", (profile_id,))
                for category in sorted({category_key(c) for c in blocked_categories if category_key(c)}):
                    conn.execute("INSERT INTO ligne1_blocked_categories(client_id,category) VALUES(?,?)", (profile_id, category))
            if flavour:
                item_no = str(flavour.get("item_no") or "").strip()
                text = str(flavour.get("value") or "").strip()
                if not item_no or len(text) > 120 or any(ord(c) < 32 for c in text):
                    raise ValueError("Le parfum nécessite un numéro d'article et une valeur sur une ligne (120 caractères maximum).")
                existing = conn.execute("SELECT revision FROM ligne1_flavours WHERE scope=? AND item_no=?", (self.scope, item_no)).fetchone()
                if (existing["revision"] if existing else 0) != flavour.get("revision", 0):
                    raise ProfileConflict("Le parfum de cet article a été modifié. Rechargez la commande.")
                conn.execute("""INSERT INTO ligne1_flavours(scope,item_no,flavour) VALUES(?,?,?)
                    ON CONFLICT(scope,item_no) DO UPDATE SET flavour=excluded.flavour,revision=revision+1,updated_at=CURRENT_TIMESTAMP""",
                    (self.scope, item_no, text))
            return self._get(conn, profile_id)

    def resolve(self, items, draft=None, draft_flavour=None, min_dlc_days_override=None):
        min_dlc_days_override = validate_min_dlc_days(min_dlc_days_override)
        result = []
        with self.db.get_connection() as conn:
            flavours = {r["item_no"]: dict(r) for r in conn.execute("SELECT * FROM ligne1_flavours WHERE scope=?", (self.scope,))}
        profiles = {}
        # Une ligne peut revenir du navigateur déjà répartie sur plusieurs lots.
        # On la regroupe avant recalcul pour que chaque actualisation reste idempotente.
        grouped_sources = []
        grouped_by_key = {}
        for source in items:
            if not source.get("BCScope"):
                grouped_sources.append(source)
                continue
            key = str(source.get("BCOrderLineKey") or "|".join(str(source.get(name) or "") for name in (
                "BCOrderNumber", "Item_No", "UnitOfMeasureCode", "Libelle"
            )))
            if key not in grouped_by_key:
                grouped_by_key[key] = dict(source)
                grouped_sources.append(grouped_by_key[key])
                continue
            existing = grouped_by_key[key]
            existing["_selected"] = bool(existing.get("_selected") or source.get("_selected"))
            if source.get("LotManuallySelected"):
                for field in ("Numlot", "CodeBarre10", "CodeBarre17", "LotManuallySelected", "LotManualOverride"):
                    existing[field] = source.get(field)
        lot_reservations = {}
        for source in grouped_sources:
            item = dict(source)
            key = (item.get("CustomerId"), item.get("CustomerNumber"), item.get("Client"))
            if key not in profiles:
                profiles[key] = self.find(item)
            profile = profiles[key]
            temporary_days = bool(item.get("ClientMinDlcDaysTransient"))
            min_days = min_dlc_days_override if temporary_days else (profile.get("min_dlc_days") if profile else None)
            item["ClientMinDlcDays"] = min_days
            item["ClientMinimumDlcDate"] = None
            category = category_key(item.get("ItemCategoryCode"))
            item["ItemCategoryCode"] = category
            item["ClientCategoryBlocked"] = bool(profile and profile["active"] and category in profile.get("blocked_categories", []))
            correction = flavours.get(item.get("Item_No"))
            item["Parfum"] = correction["flavour"] if correction else propose_flavour(item.get("ItemDescription2") or item.get("ItemDescription") or item.get("Libelle"))
            item["ParfumRevision"] = correction["revision"] if correction else 0
            item["ParfumConfirmed"] = bool(correction)
            if draft_flavour is not None:
                item["Parfum"] = str(draft_flavour)
            rule = next((r for r in (profile or {}).get("rules", []) if r["category"] == category and r["enabled"]), None)
            if not profile or not profile["active"]:
                rule = None
            if draft is not None:
                rule = draft
            template_300 = (rule or {}).get("template_300", DEFAULT_TEMPLATE)
            template_203 = (rule or {}).get("template_203", DEFAULT_TEMPLATE)
            item["ClientProfileId"] = profile["id"] if profile else None
            item["ClientProfileRevision"] = profile["revision"] if profile else None
            item["ClientProfileActive"] = bool(profile and profile["active"])
            if item.get("BCScope"):
                resolved_rows = _allocate_bc_order_line(item, min_days, lot_reservations)
            else:
                resolved_rows = [item]
            for resolved in resolved_rows:
                resolved["Libelle300"], warn300 = render_template(template_300, resolved)
                resolved["Libelle203"], warn203 = render_template(template_203, resolved)
                resolved["LabelTemplate300"] = template_300
                resolved["LabelTemplate203"] = template_203
                resolved["LabelWarnings"] = list(dict.fromkeys(warn300 + warn203))
                if not category:
                    resolved["LabelWarnings"].append("Catégorie article absente : descriptions par défaut.")
                if not correction and "${parfum}" in template_300 + template_203:
                    resolved["LabelWarnings"].append("Parfum proposé : vérifiez et confirmez sa valeur.")
                result.append(resolved)
        return result
