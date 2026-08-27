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

print("=== RECHERCHE PAR FILTRE DATE RÉCENTE OU PRODUIT ===")

# 1. Filtre par date d'écriture récente
raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Lot_No ne '' and Posting_Date ge 2026-01-01&$top=20"
url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        entries = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"Écritures 2026 trouvées ({len(entries)}) :")
        for e in entries:
            item_no = e.get('Item_No')
            desc = e.get('Item_Description')
            lot = e.get('Lot_No')
            exp_date = e.get('Expiration_Date')
            rem_qty = e.get('Remaining_Quantity')
            loc = e.get('Location_Code')
            pdate = e.get('Posting_Date')
            print(f"  * [{item_no}] {desc} | Lot: {lot} | DLC: {exp_date} | StockRestant: {rem_qty} | Date: {pdate} | Loc: {loc}")
except Exception as e:
    print(f"Erreur date 2026: {e}")

# 2. Filtre par nom de produit (ex: MONOPRIX)
raw_url2 = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=contains(Item_Description, 'MONOPRIX') and Lot_No ne ''&$top=20"
url2 = urllib.parse.quote(raw_url2, safe=":/$%?&=()'#")

try:
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp:
        entries2 = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\nÉcritures MONOPRIX trouvées ({len(entries2)}) :")
        for e in entries2:
            item_no = e.get('Item_No')
            desc = e.get('Item_Description')
            lot = e.get('Lot_No')
            exp_date = e.get('Expiration_Date')
            rem_qty = e.get('Remaining_Quantity')
            pdate = e.get('Posting_Date')
            print(f"  * [{item_no}] {desc} | Lot: {lot} | DLC: {exp_date} | StockRestant: {rem_qty} | Date: {pdate}")
except Exception as e:
    print(f"Erreur Monoprix: {e}")
