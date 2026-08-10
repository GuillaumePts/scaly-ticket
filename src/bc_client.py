import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

SECRET_FILE = Path(__file__).resolve().parent.parent / "secret.json"

class BusinessCentralClient:
    def __init__(self, secret_path: Path = SECRET_FILE):
        self.secret_path = secret_path
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if not self.secret_path.exists():
            raise FileNotFoundError(f"Le fichier de secrets {self.secret_path} est introuvable.")
        with open(self.secret_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_access_token(self) -> str:
        tenant_id = self._config["BC_TENANT_ID"]
        client_id = self._config["BC_CLIENT_ID"]
        client_secret = self._config["BC_CLIENT_SECRET"]

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://api.businesscentral.dynamics.com/.default"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res["access_token"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Erreur OAuth Microsoft ({e.code}): {error_body}")
            raise Exception(f"Échec de l'authentification OAuth Microsoft ({e.code})")

    def _normalize_order_number(self, order_number: str) -> tuple[str, str]:
        clean = order_number.strip().upper()
        digits = ''.join(c for c in clean if c.isdigit())
        if digits:
            formatted = f"V-{digits.zfill(8)}"
            return formatted, digits
        return clean, clean

    def fetch_sales_order(self, order_number: str) -> list:
        """
        Récupère les détails d'une commande client par son numéro dans Business Central.
        Accepte tout format : "269160", "00269160", "v-00269160", "V-00269160".
        """
        token = self.get_access_token()
        tenant_id = self._config["BC_TENANT_ID"]
        env = self._config.get("BC_ENVIRONMENT", "Dev")
        company_name = self._config.get("BC_COMPANY", "Ferme des Peupliers")

        target_number, raw_digits = self._normalize_order_number(order_number)

        # 1. Obtenir la liste des sociétés pour trouver l'ID correspondant
        companies_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies"
        req = urllib.request.Request(companies_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })

        try:
            with urllib.request.urlopen(req) as resp:
                companies_data = json.loads(resp.read().decode("utf-8")).get("value", [])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Erreur BC API Companies ({e.code}): {error_body}")
            raise Exception(f"Échec d'accès aux sociétés BC ({e.code}). L'application est-elle bien enregistrée dans l'environnement '{env}' ?")

        company_id = None
        for comp in companies_data:
            if comp.get("displayName", "").strip().lower() == company_name.strip().lower() or comp.get("name", "").strip().lower() == company_name.strip().lower():
                company_id = comp["id"]
                break
        
        if not company_id and companies_data:
            company_id = companies_data[0]["id"]

        if not company_id:
            raise Exception(f"Aucune société trouvée dans l'environnement BC '{env}'.")

        # 2. Chercher la commande par son numéro (tentative numéro exact / normalisé)
        order_res = self._query_orders(tenant_id, env, company_id, token, f"number eq '{target_number}'")
        
        # Fallback si pas trouvé avec eq : tenter endswith ou contains avec les chiffres
        if not order_res and raw_digits:
            order_res = self._query_orders(tenant_id, env, company_id, token, f"endswith(number, '{raw_digits}')")
            if not order_res:
                order_res = self._query_orders(tenant_id, env, company_id, token, f"contains(number, '{raw_digits}')")

        if not order_res:
            return []

        order = order_res[0]
        customer_name = order.get("customerName", "")
        order_num = order.get("number", "")
        
        # Date de livraison : tester requestedDeliveryDate, orderDate, ou date du jour
        raw_date = order.get("requestedDeliveryDate") or order.get("orderDate") or ""
        if not raw_date or raw_date.startswith("0001-01-01"):
            from datetime import datetime
            delivery_date = datetime.now().strftime("%d/%m/%y")
        else:
            # Recomposer au format DD/MM/YY si YYYY-MM-DD
            try:
                from datetime import datetime
                dt = datetime.strptime(raw_date.split("T")[0], "%Y-%m-%d")
                delivery_date = dt.strftime("%d/%m/%y")
            except Exception:
                delivery_date = raw_date

        # Numéro de lot : générer un numéro propre basé sur la date si non fourni
        from datetime import datetime
        today_str = datetime.now().strftime("%yL%d%m%y")

        # Parser les lignes de commande
        lines = order.get("salesOrderLines", [])
        results = []
        for line in lines:
            libelle = line.get("description", "")
            qty = int(line.get("quantity", 0))
            if qty > 0 and libelle:
                results.append({
                    "Client": customer_name,
                    "Commande": order_num,
                    "Libelle": libelle,
                    "DateLivraison": delivery_date,
                    "Numlot": f"LOT {today_str}",
                    "Quantite": qty
                })

        return results

    def _query_orders(self, tenant_id: str, env: str, company_id: str, token: str, filter_expr: str) -> list:
        raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({company_id})/salesOrders?$filter={filter_expr}&$expand=salesOrderLines"
        order_url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")
        req_order = urllib.request.Request(order_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })
        try:
            with urllib.request.urlopen(req_order) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", [])
        except Exception as e:
            logger.warning(f"Erreur requête BC avec filtre '{filter_expr}': {e}")
            return []
