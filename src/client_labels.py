"""Profils de libellés Ligne 1. Toutes les écritures restent dans SQLite."""
import re
import sqlite3
import unicodedata
import uuid

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
        return result

    def get(self, profile_id):
        with self.db.get_connection() as conn:
            return self._get(conn, profile_id)

    def list(self):
        with self.db.get_connection() as conn:
            return [self._get(conn, r["id"]) for r in conn.execute(
                "SELECT id FROM ligne1_clients WHERE scope=? ORDER BY display_name", (self.scope,)).fetchall()]

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

    def create(self, identity, categories=(), rules=(), active=True, blocked_categories=()):
        name = str(identity.get("Client") or "").strip()
        if not name or len(name) > 200:
            raise ValueError("Le nom du client est obligatoire (200 caractères maximum).")
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
            for category in sorted(set(CATEGORIES + list(supplied) + [category_key(c) for c in categories if category_key(c)])):
                rule = supplied.get(category, {})
                conn.execute("INSERT INTO ligne1_rules(client_id,category,template_300,template_203,enabled) VALUES(?,?,?,?,?)",
                             (profile_id, category, rule.get("template_300", DEFAULT_TEMPLATE),
                              rule.get("template_203", DEFAULT_TEMPLATE), int(rule.get("enabled", True))))
            for category in sorted({category_key(c) for c in blocked_categories if category_key(c)}):
                conn.execute("INSERT INTO ligne1_blocked_categories(client_id,category) VALUES(?,?)", (profile_id, category))
            return self._get(conn, profile_id)

    def save(self, profile_id, revision, name, active, rules, identity=None, flavour=None, blocked_categories=None):
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

    def resolve(self, items, draft=None, draft_flavour=None):
        result = []
        with self.db.get_connection() as conn:
            flavours = {r["item_no"]: dict(r) for r in conn.execute("SELECT * FROM ligne1_flavours WHERE scope=?", (self.scope,))}
        profiles = {}
        for source in items:
            item = dict(source)
            key = (item.get("CustomerId"), item.get("CustomerNumber"), item.get("Client"))
            if key not in profiles:
                profiles[key] = self.find(item)
            profile = profiles[key]
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
            item["Libelle300"], warn300 = render_template(template_300, item)
            item["Libelle203"], warn203 = render_template(template_203, item)
            item["LabelTemplate300"] = template_300
            item["LabelTemplate203"] = template_203
            item["LabelWarnings"] = list(dict.fromkeys(warn300 + warn203))
            if not category:
                item["LabelWarnings"].append("Catégorie article absente : descriptions par défaut.")
            if not correction and "${parfum}" in template_300 + template_203:
                item["LabelWarnings"].append("Parfum proposé : vérifiez et confirmez sa valeur.")
            item["ClientProfileId"] = profile["id"] if profile else None
            item["ClientProfileRevision"] = profile["revision"] if profile else None
            item["ClientProfileActive"] = bool(profile and profile["active"])
            result.append(item)
        return result
