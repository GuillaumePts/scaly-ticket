import sys
sys.path.insert(0, '.')
import json
import urllib.request
import urllib.parse
from src.bc_client import BusinessCentralClient

bc = BusinessCentralClient()
token = bc.get_access_token()
tenant_id = bc._config['BC_TENANT_ID']
env = 'Dev'
headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/json'
}

comp_name = "Ferme des Peupliers"
comp_encoded = urllib.parse.quote(comp_name)

print("=== TEST DE RECHERCHE DE LOT ET DLC PAR PRODUIT DANS ITEMLEDGERENTRIES ===")

def find_lot_for_product(libelle: str, min_date: str = "2020-01-01"):
    # Normalisation des mots clés du libellé
    keywords = [w for w in libelle.lower().replace('.', ' ').replace('-', ' ').split() if len(w) > 3 and w not in ['yaourt', 'monoprix', 'entier']]
    
    # Construction du filtre
    if keywords:
        kw_filter = f"contains(Item_Description, '{keywords[0]}')"
    else:
        kw_filter = f"contains(Item_Description, '{libelle[:10]}')"
        
    raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter={kw_filter} and Lot_No ne ''&$top=5"
    url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            entries = json.loads(resp.read().decode('utf-8')).get('value', [])
            if entries:
                # Trier par Expiration_Date
                return entries[0]
    except Exception as e:
        print(f"Erreur recherche pour '{libelle}': {e}")
    return None

import time

def query_with_retry(fn, max_retries=3):
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if i == max_retries - 1:
                raise e
            time.sleep(1.5)

# Test sur les lignes de la commande 266124
order_res = query_with_retry(lambda: bc._query_orders(tenant_id, env, "46a34776-0a36-ef11-8409-00224838bfdb", token, "contains(number, '266124')"))
if order_res:
    order = order_res[0]
    print(f"\nCommande: {order.get('number')} pour {order.get('customerName')}")
    lines = order.get('salesOrderLines', [])
    for line in lines:
        lib = line.get('description')
        qty = line.get('quantity')
        lot_entry = find_lot_for_product(lib)
        if lot_entry:
            print(f"  * [{lib}] Qte: {qty} -> TROUVÉ : Lot '{lot_entry.get('Lot_No')}' | DLC '{lot_entry.get('Expiration_Date')}' (Art: {lot_entry.get('Item_Description')})")
        else:
            print(f"  * [{lib}] Qte: {qty} -> Aucun lot trouvé dans la table")
