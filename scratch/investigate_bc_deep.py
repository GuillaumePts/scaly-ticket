import sys
sys.path.insert(0, '.')
import json
import urllib.request
import urllib.parse
import time
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

def safe_get(url, label=""):
    encoded_url = urllib.parse.quote(url, safe=":/$%?&=()'#")
    for attempt in range(3):
        try:
            req = urllib.request.Request(encoded_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < 2:
                time.sleep(1.5)
            else:
                print(f"  ERREUR {label}: {e}")
                return None

# =============================================
# 1. LOTS RÉCENTS 2026 - Le vrai format des lots !
# =============================================
print("=" * 70)
print("[1] LOTS RÉCENTS 2026 (ItemLedgerEntries)")
print("    Le $top=200 sans filtre date retournait les plus vieux en premier !")
print("=" * 70)
data = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Lot_No ne '' and Posting_Date ge 2026-01-01 and Remaining_Quantity gt 0&$top=20",
    "Lots 2026"
)
if data and data.get('value'):
    for e in data['value']:
        item_no = e.get('Item_No', '')
        desc = e.get('Item_Description', '')
        lot = e.get('Lot_No', '')
        dlc = e.get('Expiration_Date', '')
        rem = e.get('Remaining_Quantity', 0)
        ref = e.get('Item_Reference_No', '')
        loc = e.get('Location_Code', '')
        pdate = e.get('Posting_Date', '')
        print(f"  [{item_no}] {desc} | Lot: {lot} | DLC: {dlc} | Stock: {rem} | Ref: {ref} | Loc: {loc} | Date: {pdate}")

# =============================================
# 2. CHERCHER LES GTIN-14 VIA workflowItems
# =============================================
print("\n" + "=" * 70)
print("[2] TABLE workflowItems - Champs disponibles")
print("=" * 70)
data_wf = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/workflowItems?$top=1",
    "workflowItems"
)
if data_wf and data_wf.get('value'):
    for k, v in data_wf['value'][0].items():
        if k != '@odata.etag':
            print(f"  {k}: {v}")

# =============================================
# 3. TESTER L'API v2.0 /items (différent de OData Y27Item)
# =============================================
print("\n" + "=" * 70)
print("[3] API v2.0 /items (standard Microsoft)")
print("=" * 70)
comp_id = "46a34776-0a36-ef11-8409-00224838bfdb"
data_items = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({comp_id})/items?$top=3&$select=id,number,displayName,gtin,itemCategoryCode,baseUnitOfMeasureCode",
    "API v2.0 items"
)
if data_items and data_items.get('value'):
    for it in data_items['value']:
        print(f"  No: {it.get('number')} | Nom: {it.get('displayName')} | GTIN: {it.get('gtin')} | Cat: {it.get('itemCategoryCode')}")

# Chercher un article vanille via API v2.0
data_vanille = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({comp_id})/items?$filter=contains(displayName, 'Vanille')&$top=10&$select=id,number,displayName,gtin,itemCategoryCode",
    "API v2.0 items Vanille"
)
if data_vanille and data_vanille.get('value'):
    print("\n  Articles Vanille :")
    for it in data_vanille['value']:
        print(f"    No: {it.get('number')} | Nom: {it.get('displayName')} | GTIN: {it.get('gtin')}")

# =============================================
# 4. VÉRIFIER LES CHAMPS COMPLETS D'UNE ENTRÉE 2026
# =============================================
print("\n" + "=" * 70)
print("[4] TOUS LES CHAMPS D'UNE ENTRÉE DE LOT 2026")
print("=" * 70)
if data and data.get('value'):
    first = data['value'][0]
    for k, v in first.items():
        if k != '@odata.etag':
            print(f"  {k}: {v}")
