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

print("=== RECHERCHE DES FABRICATIONS RÉELLES (Entry_Type eq 'Output') ===")

raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Entry_Type eq 'Output' and Lot_No ne ''&$top=15"
url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")

import time

for attempt in range(3):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            entries = json.loads(resp.read().decode('utf-8')).get('value', [])
            print(f"Écritures de fabrication trouvées ({len(entries)}) :")
            for e in entries:
                item_no = e.get('Item_No')
                desc = e.get('Item_Description')
                lot = e.get('Lot_No')
                exp_date = e.get('Expiration_Date')
                rem_qty = e.get('Remaining_Quantity')
                pdate = e.get('Posting_Date')
                qty = e.get('Quantity')
                print(f"  * [{item_no}] {desc} | Lot: {lot} | DLC: {exp_date} | QteFab: {qty} | StockRestant: {rem_qty} | Date: {pdate}")
            break
    except Exception as e:
        print(f"Tentative {attempt+1}/3 échouée : {e}")
        time.sleep(2)
