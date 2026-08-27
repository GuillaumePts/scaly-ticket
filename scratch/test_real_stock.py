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

print("=== RECHERCHE DES LOTS EN STOCK ACTIF (Open eq true et Remaining_Quantity gt 0) ===")

# Filtrer les écritures avec du stock restant
raw_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Open eq true and Remaining_Quantity gt 0&$top=15"
url = urllib.parse.quote(raw_url, safe=":/$%?&=()'#")
print(f"URL: {url}")

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        entries = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\nÉcritures de stock actif trouvées ({len(entries)}) :")
        for e in entries:
            item_no = e.get('Item_No')
            desc = e.get('Item_Description')
            lot = e.get('Lot_No')
            exp_date = e.get('Expiration_Date')
            rem_qty = e.get('Remaining_Quantity')
            loc = e.get('Location_Code')
            ref = e.get('Item_Reference_No')
            print(f"  * Article: [{item_no}] {desc} | Lot: {lot} | DLC: {exp_date} | Stock: {rem_qty} | Loc: {loc} | Ref: {ref}")
except urllib.error.HTTPError as e:
    print(f"Erreur HTTP ({e.code}): {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Erreur: {e}")
