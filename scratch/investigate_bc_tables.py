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
    """GET avec retry et gestion d'erreur propre"""
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
# 1. CHERCHER LES GTIN-14 DANS LA TABLE ARTICLES (Y27Item)
# =============================================
print("=" * 60)
print("[1] TABLE Y27Item (Fiche Article) - Champs disponibles")
print("=" * 60)
data = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y27Item?$top=1",
    "Y27Item"
)
if data and data.get('value'):
    for k, v in data['value'][0].items():
        if k != '@odata.etag':
            print(f"  {k}: {v}")

# Chercher un article avec "vanille" pour voir le GTIN
print("\n[1b] Recherche d'un article Vanille dans Y27Item :")
data_v = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y27Item?$filter=contains(Description, 'Vanille')&$top=5",
    "Y27Item Vanille"
)
if data_v and data_v.get('value'):
    for item in data_v['value']:
        print(f"  * No: {item.get('No')} | Desc: {item.get('Description')} | GTIN: {item.get('GTIN', 'N/A')} | Base_UoM: {item.get('Base_Unit_of_Measure', 'N/A')}")
        # Afficher TOUS les champs qui contiennent "bar" ou "gtin" ou "ean" ou "ref"
        for k, v in item.items():
            kl = k.lower()
            if any(x in kl for x in ['bar', 'gtin', 'ean', 'ref', 'cross', 'upc']):
                print(f"    >> {k}: {v}")

# =============================================
# 2. CHERCHER UNE TABLE DE RÉFÉRENCES CROISÉES (Item Cross Reference / Item Reference)
# =============================================
print("\n" + "=" * 60)
print("[2] RECHERCHE DE TABLES DE RÉFÉRENCES ARTICLES")
print("=" * 60)

# Lister tous les services OData qui contiennent "ref", "cross", "item" ou "barcode"
odata_root = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4",
    "ODataV4 root"
)
if odata_root and odata_root.get('value'):
    relevant = []
    for svc in odata_root['value']:
        name = svc.get('name', '').lower()
        if any(x in name for x in ['ref', 'cross', 'barcode', 'gtin', 'ean', 'item', 'vue_de_stock']):
            relevant.append(svc.get('name'))
    print(f"  Services potentiels ({len(relevant)}) :")
    for r in relevant:
        print(f"    - {r}")

# =============================================
# 3. TESTER Vue_de_stock_Excel (pourrait contenir les GTIN et lots)
# =============================================
print("\n" + "=" * 60)
print("[3] TABLE Vue_de_stock_Excel - Champs disponibles")
print("=" * 60)
data_stock = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Vue_de_stock_Excel?$top=1",
    "Vue_de_stock_Excel"
)
if data_stock and data_stock.get('value'):
    for k, v in data_stock['value'][0].items():
        if k != '@odata.etag':
            print(f"  {k}: {v}")

# =============================================
# 4. COMPRENDRE LES DATES - Compter les entrées par année
# =============================================
print("\n" + "=" * 60)
print("[4] DIAGNOSTIC DES DATES (ItemLedgerEntries)")
print("=" * 60)
for year in ['2026', '2025', '2024', '2020', '2015', '2010']:
    data_y = safe_get(
        f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$filter=Lot_No ne '' and Posting_Date ge {year}-01-01 and Posting_Date lt {str(int(year)+1)}-01-01&$top=1&$count=true",
        f"Count {year}"
    )
    if data_y:
        count = data_y.get('@odata.count', len(data_y.get('value', [])))
        sample = data_y['value'][0] if data_y.get('value') else None
        desc = sample.get('Item_Description', '') if sample else ''
        lot = sample.get('Lot_No', '') if sample else ''
        print(f"  {year}: count={count} | Exemple: {desc} Lot={lot}")
    else:
        print(f"  {year}: Aucune donnée ou erreur")
