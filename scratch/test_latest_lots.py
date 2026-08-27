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

print("=== RECHERCHE DES DERNIÈRES ENTRÉES DE LOTS RÉCENTES (Posting_Date desc) ===")

raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Lot_No ne ''&$orderby=Posting_Date desc&$top=20"
url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        entries = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"Écritures trouvées ({len(entries)}) :")
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
    print(f"Erreur: {e}")
