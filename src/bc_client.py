import json
import math
import logging
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

from src.config import exe_directory, base_path

def normalize_lot_number(lot) -> str:
    """Normalise un lot BC pour le texte imprimé et le GS1-128."""
    if lot is None:
        return ""
    return str(lot).strip().replace("/", "")

def get_secret_file() -> Path:
    # 1. Vérifier à côté de l'exécutable
    p_exe = exe_directory / "secret.json"
    if p_exe.exists():
        return p_exe
    # 2. Vérifier dans le bundle interne
    p_base = base_path / "secret.json"
    if p_base.exists():
        return p_base
    return p_exe

class BusinessCentralClient:
    def __init__(self, secret_path: Path = None):
        self.secret_path = secret_path or get_secret_file()
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

    def _get_configured_company_id(self, token: str, tenant_id: str, env: str) -> str:
        """Résout l'entreprise BC configurée en lecture seule."""
        configured_id = self._config.get("BC_COMPANY_ID")
        if configured_id:
            return configured_id

        company_name = self._config.get("BC_COMPANY", "Ferme des Peupliers")
        companies_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies"
        req = urllib.request.Request(companies_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                companies = json.loads(resp.read().decode("utf-8")).get("value", [])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Erreur BC API Companies ({e.code}): {error_body}")
            raise Exception(f"Échec d'accès aux sociétés BC ({e.code}) dans l'environnement '{env}'.")

        for company in companies:
            display_name = company.get("displayName", "").strip().lower()
            name = company.get("name", "").strip().lower()
            if display_name == company_name.strip().lower() or name == company_name.strip().lower():
                return company["id"]

        raise Exception(f"La société BC '{company_name}' est introuvable dans l'environnement '{env}'.")

    def fetch_production_order_raw(self, production_order_number: str) -> dict:
        """Effectue uniquement le GET de test sur un O.F. de Business Central.

        Cette méthode vise l'Analytics API manufacturingProductionOrders et ne fait
        aucune opération d'écriture dans Business Central.
        """
        of_number = str(production_order_number or "").strip()
        if not of_number:
            raise ValueError("Le numéro d'O.F. est obligatoire.")

        token = self.get_access_token()
        tenant_id = self._config["BC_TENANT_ID"]
        env = self._config.get("BC_ENVIRONMENT", "Dev")
        if env.strip().lower() not in {"dev", "development", "sandbox", "test"}:
            raise Exception(
                f"Appel O.F. bloqué : l'environnement configuré est '{env}', pas un environnement de développement."
            )

        company_id = self._get_configured_company_id(token, tenant_id, env)
        escaped_of = of_number.replace("'", "''")
        filter_expr = urllib.parse.quote(f"no eq '{escaped_of}'", safe="()'$")
        url = (
            "https://api.businesscentral.dynamics.com/"
            f"v2.0/{env}/api/microsoft/analytics/v1.0/companies({company_id})/"
            f"manufacturingProductionOrders?$filter={filter_expr}"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Erreur GET O.F. BC ({e.code}): {error_body}")
            raise Exception(f"Échec du GET O.F. Business Central ({e.code}).")

    def _fetch_production_order_lines_raw(
        self,
        production_order_number: str,
        token: str,
        tenant_id: str,
        env: str,
        company_id: str,
    ) -> list:
        """Récupère les lignes d'un O.F. via un GET Analytics API."""
        escaped_of = production_order_number.replace("'", "''")
        filter_expr = urllib.parse.quote(f"prodOrderNo eq '{escaped_of}'", safe="()'$")
        url = (
            "https://api.businesscentral.dynamics.com/"
            f"v2.0/{env}/api/microsoft/analytics/v1.0/companies({company_id})/"
            f"manufacturingProdOrderLines?$filter={filter_expr}"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", [])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"Erreur GET lignes O.F. BC ({e.code}): {error_body}")
            raise Exception(f"Échec de récupération des lignes de l'O.F. ({e.code}).")

    def _fetch_production_output_lots_raw(
        self,
        production_order_number: str,
        token: str,
        env: str,
        company_id: str,
    ) -> list:
        """Récupère les lots de sortie déjà enregistrés pour un O.F."""
        escaped_of = production_order_number.replace("'", "''")
        filter_expr = urllib.parse.quote(
            f"orderNo eq '{escaped_of}' and entryType eq 'Output'",
            safe="()'$",
        )
        url = (
            "https://api.businesscentral.dynamics.com/"
            f"v2.0/{env}/api/microsoft/analytics/v1.0/companies({company_id})/"
            f"prodItemLedgerEntries?$filter={filter_expr}"
        )
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", [])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.warning(f"Impossible de récupérer les lots de sortie de l'O.F. ({e.code}): {error_body}")
            return []

    @staticmethod
    def _format_bc_date(value, gs1: bool = False) -> str:
        """Convertit une date BC ISO en affichage français ou YYMMDD."""
        raw = str(value or "").strip()
        if not raw or raw.startswith("0001-01-01"):
            return ""
        try:
            from datetime import datetime
            date_value = datetime.strptime(raw.split("T")[0], "%Y-%m-%d")
            return date_value.strftime("%y%m%d" if gs1 else "%d/%m/%Y")
        except (TypeError, ValueError):
            return raw

    @staticmethod
    def _build_production_lot(value) -> str:
        """Construit un lot de production au format YYLWWDDMM."""
        raw = str(value or "").strip()
        if not raw or raw.startswith("0001-01-01"):
            return ""
        try:
            from datetime import datetime
            date_value = datetime.strptime(raw.split("T")[0], "%Y-%m-%d")
            iso_week = date_value.isocalendar().week
            return f"{date_value:%y}L{iso_week:02d}{date_value:%d%m}"
        except (TypeError, ValueError):
            return ""

    def fetch_conditionnement_production_order(self, production_order_number: str) -> dict:
        """Prépare les lignes d'un O.F. pour les étiquettes Conditionnement.

        Les quantités BC sont exprimées en pots. L'impression se fait en cartons
        de six pots, avec un arrondi systématique à l'entier supérieur.
        """
        raw_order = self.fetch_production_order_raw(production_order_number)
        orders = raw_order.get("value", [])
        if not orders:
            return {
                "items": [],
                "raw": {
                    "productionOrders": raw_order,
                    "productionOrderLines": [],
                    "prodItemLedgerEntries": [],
                },
            }

        header = orders[0]
        of_number = header.get("no") or str(production_order_number).strip()
        token = self.get_access_token()
        tenant_id = self._config["BC_TENANT_ID"]
        env = self._config.get("BC_ENVIRONMENT", "Dev")
        company_id = self._get_configured_company_id(token, tenant_id, env)
        lines = self._fetch_production_order_lines_raw(
            of_number, token, tenant_id, env, company_id
        )
        output_entries = self._fetch_production_output_lots_raw(
            of_number, token, env, company_id
        )

        # Un O.F. standard possède normalement au moins une ligne. Le fallback
        # sur l'en-tête permet de conserver un résultat exploitable si l'API ne
        # publie pas encore les lignes dans cet environnement de développement.
        source_lines = lines or [header]
        from src.config import db
        from src.main import find_ean13_for_libelle

        parfums_list = db.get_parfums()

        output_by_item = {}
        for entry in output_entries:
            item_no = entry.get("itemNo") or ""
            lot = normalize_lot_number(entry.get("lotNo", ""))
            if item_no and lot:
                output_by_item.setdefault(item_no, []).append(entry)

        results = []
        for line in source_lines:
            item_no = line.get("itemNo") or line.get("itemNumber") or ""
            libelle = (
                line.get("itemDescription")
                or line.get("description")
                or header.get("description")
                or item_no
                or f"O.F. {of_number}"
            )

            raw_quantity = (
                line.get("quantityBase")
                if line.get("quantityBase") is not None
                else line.get("quantity")
            )
            if raw_quantity is None:
                raw_quantity = header.get("quantity", 0)
            try:
                pots_quantity = float(raw_quantity or 0)
            except (TypeError, ValueError):
                pots_quantity = 0
            if pots_quantity <= 0:
                continue

            cartons_quantity = int(math.ceil(pots_quantity / 6))
            match = find_ean13_for_libelle(libelle, parfums_list)
            gtin = ""
            if match:
                gtin = match.get("gtin14") or match.get("ean13", "")

            produced_entries = output_by_item.get(item_no, [])
            if not produced_entries and len(output_entries) == 1:
                produced_entries = output_entries
            available_lots = []
            for entry in produced_entries:
                lot = normalize_lot_number(entry.get("lotNo", ""))
                if lot and not any(option["lot"] == lot for option in available_lots):
                    available_lots.append({
                        "lot": lot,
                        "dlc_display": self._format_bc_date(entry.get("expirationDate")),
                        "code_barre_17": self._format_bc_date(entry.get("expirationDate"), gs1=True),
                        "qty": float(entry.get("quantity", 0) or 0),
                        "blocked": False,
                    })

            selected_lot = available_lots[0] if available_lots else None
            due_date_raw = line.get("dueDate") or header.get("dueDate")
            lot = selected_lot["lot"] if selected_lot else normalize_lot_number(
                line.get("lotNo") or line.get("lotNumber") or header.get("lotNo") or ""
            )
            if not lot:
                lot = self._build_production_lot(due_date_raw)

            # La DLC n'est pas encore définie par le service qualité : elle doit
            # rester vide même si BC expose un champ de date sur une écriture.
            expiration = ""
            due_date = self._format_bc_date(due_date_raw)

            pot_value = int(pots_quantity) if pots_quantity.is_integer() else pots_quantity
            results.append({
                "Client": "Conditionnement",
                "Commande": of_number,
                "Libelle": libelle,
                "DateLivraison": due_date,
                "Item_No": item_no,
                "CodeBarre01": gtin,
                "CodeBarre17": expiration,
                "CodeBarre10": lot,
                "Numlot": lot,
                "Quantite": cartons_quantity,
                "QuantitePots": pot_value,
                "QuantiteCartons": cartons_quantity,
                "available_lots": available_lots,
                "OFStatut": header.get("status", ""),
            })

        return {
            "items": results,
            "raw": {
                "productionOrders": raw_order,
                "productionOrderLines": lines,
                "prodItemLedgerEntries": output_entries,
            },
        }

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

        # 2b. Extraire tous les identifiants d'articles uniques de la commande
        lines = order.get("salesOrderLines", [])
        order_item_nos = list(set([
            line.get("lineObjectNumber", line.get("number", "")) 
            for line in lines 
            if line.get("lineObjectNumber") or line.get("number")
        ]))
        
        # 3. Récupérer la table des lots en stock (ItemLedgerEntries) via GET avec filtre STRICT
        stock_lots = self._fetch_stock_lots(tenant_id, env, comp.get("name", company_name), token, item_nos=order_item_nos)

        # 4. Récupérer les références article BC pour les codes d'étiquette.
        #    Le service OData est lu en une seule fois pour tous les articles
        #    de la commande. Aucune référence locale n'est utilisée ici.
        item_references = self._fetch_item_references(
            tenant_id,
            env,
            comp.get("displayName", company_name),
            token,
            item_nos=order_item_nos,
        )
        
        # 4b. Calculer la date de DLC minimale (strictement >= Date du jour)
        from datetime import datetime
        min_dlc_date = datetime.now()

        # 5. Parser les lignes de commande et construire les 9 colonnes complètes
        lines = order.get("salesOrderLines", [])
        results = []
        for line in lines:
            libelle = line.get("description", "")
            qty = int(line.get("quantity", 0))
            if qty <= 0 or not libelle:
                continue

            # A. Résolution des références selon l'article et l'unité de la ligne.
            #    EAN14 sert aux étiquettes carton (300 dpi), GENCOD aux pots (203 dpi).
            item_no = line.get("lineObjectNumber", line.get("number", ""))
            unit_of_measure = (line.get("unitOfMeasureCode") or "").strip()
            code_barre_01 = self._find_item_reference(
                item_references, item_no, unit_of_measure, "EAN14"
            )
            gencod = self._find_item_reference(
                item_references, item_no, unit_of_measure, "GENCOD"
            )
            if not code_barre_01:
                logger.warning(
                    "Aucun EAN14 BC pour l'article %s avec l'unité %s",
                    item_no,
                    unit_of_measure or "(vide)",
                )

            # B. Recherche du vrai numéro de lot et DLC dans la table BC
            candidates = self._get_all_lots_for_libelle(libelle, stock_lots, min_dlc_date, item_no=item_no)
            available_lots = []
            
            from datetime import datetime
            for c in candidates:
                lot = normalize_lot_number(c.get('Lot_No', ''))
                qty = float(c.get('Remaining_Quantity', 0))
                dlc_raw = c.get('Expiration_Date', '').split('T')[0]
                
                try:
                    dt_dlc = datetime.strptime(dlc_raw, "%Y-%m-%d")
                    dlc_display = dt_dlc.strftime("%d/%m/%Y")
                    code_barre_17 = dt_dlc.strftime("%y%m%d")
                except:
                    dlc_display = dlc_raw
                    code_barre_17 = ""
                    
                blocked = "BLOQUE" in lot.upper() or c.get('Quality_Blocked', False)
                available_lots.append({
                    "lot": lot,
                    "dlc_display": dlc_display,
                    "code_barre_17": code_barre_17,
                    "qty": qty,
                    "blocked": blocked
                })
            
            if candidates:
                matched_lot = candidates[0]
                lot_no = normalize_lot_number(matched_lot.get("Lot_No", ""))
                exp_raw = matched_lot.get("Expiration_Date", "")
                try:
                    dt_exp = datetime.strptime(exp_raw.split("T")[0], "%Y-%m-%d")
                    code_barre_17 = dt_exp.strftime("%y%m%d")
                    dlc_display = dt_exp.strftime("%d/%m/%y")
                except Exception:
                    code_barre_17 = ""
                    dlc_display = exp_raw
            else:
                lot_no = ""
                code_barre_17 = ""
                dlc_display = delivery_date

            # C. Formatage du Numlot et CodeBarre10
            code_barre_10 = lot_no
            num_lot_text = lot_no

            results.append({
                "Client": customer_name,
                "Commande": order_num,
                "Libelle": libelle,
                "DateLivraison": delivery_date,
                "Item_No": item_no,
                "UnitOfMeasureCode": unit_of_measure,
                "CodeBarre01": code_barre_01,
                "GENCOD": gencod,
                "CodeBarre17": code_barre_17,
                "CodeBarre10": code_barre_10,
                "Numlot": num_lot_text,
                "Quantite": qty,
                "available_lots": available_lots
            })

        # INJECTION POUR DEBUG : Ajouter la réponse brute BC à la première ligne pour la console web
        if results and len(results) > 0:
            results[0]["_raw_bc_order"] = order

        return results

    def _fetch_item_references(
        self,
        tenant_id: str,
        env: str,
        company_name: str,
        token: str,
        item_nos: list[str] | None = None,
    ) -> list[dict]:
        """Récupère les références article via le service OData BC en lecture seule."""
        item_nos = sorted({str(item_no).strip() for item_no in (item_nos or []) if str(item_no).strip()})
        if not item_nos:
            return []

        filters = " or ".join(
            f"Item_No eq '{item_no.replace(chr(39), chr(39) * 2)}'"
            for item_no in item_nos
        )
        company = urllib.parse.quote(company_name, safe="")
        base_url = (
            f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}"
            f"/ODataV4/Company('{company}')/ScalyItemReferences"
        )
        query = urllib.parse.urlencode({"$filter": filters, "$top": "1000", "$format": "json"})
        url = f"{base_url}?{query}"
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", [])
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error("Erreur GET OData références article (%s): %s", e.code, error_body)
            raise Exception(
                f"Impossible de récupérer les références article BC ({e.code}). "
                "Vérifiez le service OData ScalyItemReferences et ses permissions de lecture."
            ) from e
        except Exception as e:
            logger.error("Erreur GET OData références article: %s", e)
            raise Exception("Impossible de joindre le service OData des références article BC.") from e

    @staticmethod
    def _find_item_reference(
        references: list[dict],
        item_no: str,
        unit_of_measure: str,
        reference_type_no: str,
    ) -> str:
        """Sélectionne une référence BC par article, unité et type (EAN14/GENCOD)."""
        item_no = (item_no or "").strip().upper()
        unit_of_measure = (unit_of_measure or "").strip().upper()
        reference_type_no = (reference_type_no or "").strip().upper()

        matches = [
            ref for ref in references
            if str(ref.get("Item_No", "")).strip().upper() == item_no
            and str(ref.get("Unit_of_Measure", "")).strip().upper() == unit_of_measure
            and str(ref.get("Reference_Type", "")).strip().upper() == "BAR CODE"
            and str(ref.get("Reference_Type_No", "")).strip().upper() == reference_type_no
        ]
        return str(matches[0].get("Reference_No", "")).strip() if matches else ""

    def _fetch_stock_lots(self, tenant_id: str, env: str, company_name: str, token: str, item_nos: list = None) -> list:
        """Récupère en lecture seule (GET) les écritures de lots réelles de Business Central."""
        import time
        comp_encoded = urllib.parse.quote(company_name)
        
        # Filtre de base
        base_filter = "Lot_No ne '' and Posting_Date ge 2026-01-01 and Remaining_Quantity gt 0"
        
        if item_nos:
            # Filtrage STRICT sur les articles de la commande (méthode robuste)
            item_filters = " or ".join([f"Item_No eq '{i}'" for i in item_nos if i])
            if item_filters:
                base_filter += f" and ({item_filters})"
                
        # On augmente le $top car on cible maintenant précisément les bons articles
        raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter={base_filter}&$top=1000"
        url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    return json.loads(resp.read().decode("utf-8")).get("value", [])
            except Exception as e:
                logger.warning(f"Tentative {attempt+1} lecture ItemLedgerEntries : {e}")
                time.sleep(1.5)
        return []

    def _get_all_lots_for_libelle(self, libelle: str, stock_lots: list, min_dlc_date, item_no: str = None) -> list:
        """Retourne tous les lots pertinents en se basant sur le code article exact (Item_No) si fourni."""
        from datetime import datetime
        
        candidates = []
        for e in stock_lots:
            lot = e.get('Lot_No', '')
            dlc_raw = e.get('Expiration_Date', '')
            qty = float(e.get('Remaining_Quantity', 0))
            e_item_no = e.get('Item_No', '')
            
            # BLOQUER STRICTEMENT LES QUANTITÉS <= 0
            if not lot or not dlc_raw or dlc_raw.startswith('0001') or qty <= 0:
                continue
                
            try:
                dt_dlc = datetime.strptime(dlc_raw.split("T")[0], "%Y-%m-%d")
                if min_dlc_date and dt_dlc.date() < min_dlc_date.date():
                    continue 
            except:
                pass
                
            # Si on a l'Item_No exact, on ne prend QUE ça
            if item_no and e_item_no:
                if e_item_no == item_no:
                    candidates.append(e)
                continue
                
            # Fallback textuel très basique si on n'a vraiment pas d'item_no
            import unicodedata, re
            def norm(s):
                s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower()
                return re.sub(r'[^a-z0-9]', ' ', s)
                
            desc = norm(e.get('Item_Description', ''))
            lib_clean = norm(libelle)
            
            flavors = ['vanille', 'fraise', 'framboise', 'myrtille', 'nature', 'abricot', 'citron', 'noisette', 'poire', 'cerise', 'litchi', 'caramel', 'cafe', 'chocolat', 'marron', 'peche', 'miel']
            found_flavor = next((f for f in flavors if f in lib_clean), None)
            
            if found_flavor and found_flavor in desc:
                candidates.append(e)
            elif not found_flavor and ('nature' in desc if 'nature' in lib_clean else True):
                candidates.append(e)
                
        # Trier par date de péremption la plus proche
        candidates.sort(key=lambda x: x.get('Expiration_Date', ''))
        return candidates

    def _match_lot_for_libelle(self, libelle: str, stock_lots: list, min_dlc_date, item_no: str = None) -> dict:
        """Trouve le lot et la DLC les plus pertinents pour un produit selon la méthode FEFO."""
        candidates = self._get_all_lots_for_libelle(libelle, stock_lots, min_dlc_date, item_no)
        if candidates:
            return candidates[0]
        return None

    def _query_orders(self, tenant_id: str, env: str, company_id: str, token: str, filter_expr: str) -> list:
        raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({company_id})/salesOrders?$filter={filter_expr}&$expand=salesOrderLines"
        order_url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")
        req_order = urllib.request.Request(order_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })
        try:
            with urllib.request.urlopen(req_order, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8")).get("value", [])
        except Exception as e:
            logger.warning(f"Erreur requête BC avec filtre '{filter_expr}': {e}")
            return []
