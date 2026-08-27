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

print("=== TEST RÉCUPÉRATION BATCH EN 1 SEULE REQUÊTE GET ===")

# 1. Récupérer toutes les écritures de lots récentes en UNE SEULE requête GET
raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Lot_No ne ''&$top=150"
url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    stock_entries = json.loads(resp.read().decode('utf-8')).get('value', [])

print(f"Table de lots chargée en mémoire : {len(stock_entries)} écritures.")

# 2. Algorithme de matching local ultra rapide (FEFO + Mots-clés)
def match_lot_locally(libelle: str, entries: list):
    import unicodedata, re
    
    def norm(s):
        s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower()
        return re.sub(r'[^a-z0-9]', ' ', s)
        
    lib_clean = norm(libelle)
    flavors = ['vanille', 'fraise', 'framboise', 'myrtille', 'nature', 'abricot', 'citron', 'noisette', 'poire', 'cerise', 'litchi', 'caramel', 'cafe', 'chocolat']
    
    found_flavor = next((f for f in flavors if f in lib_clean), None)
    
    candidates = []
    for e in entries:
        desc = norm(e.get('Item_Description', ''))
        lot = e.get('Lot_No')
        dlc = e.get('Expiration_Date')
        if not lot or not dlc or dlc.startswith('0001'):
            continue
            
        if found_flavor and found_flavor in desc:
            candidates.append(e)
        elif not found_flavor and ('nature' in desc if 'nature' in lib_clean else True):
            candidates.append(e)
            
    if candidates:
        # Trier par DLC (FEFO)
        candidates.sort(key=lambda x: x.get('Expiration_Date', ''))
        return candidates[0]
    return None

# 3. Appliquer sur la commande 266124
order_res = bc._query_orders(tenant_id, env, "46a34776-0a36-ef11-8409-00224838bfdb", token, "contains(number, '266124')")
if order_res:
    lines = order_res[0].get('salesOrderLines', [])
    print(f"\nRésultat pour la commande {order_res[0].get('number')} :")
    for l in lines:
        lib = l.get('description')
        qty = l.get('quantity')
        matched = match_lot_locally(lib, stock_entries)
        if matched:
            lot = matched.get('Lot_No')
            dlc = matched.get('Expiration_Date')
            # Formater au standard GS1
            dlc_clean = dlc.replace('-', '')[2:] if dlc else ''
            print(f"  [OK] {lib} (Qte: {qty}) => Lot: '{lot}' | DLC: {dlc} (GS1 CodeBarre17: {dlc_clean})")
        else:
            print(f"  [?]  {lib} (Qte: {qty}) => Pas de lot correspondant dans l'extrait")
