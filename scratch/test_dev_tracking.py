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

# 1. Obtenir l'ID de la société Ferme des Peupliers
companies_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies"
req = urllib.request.Request(companies_url, headers=headers)
with urllib.request.urlopen(req) as resp:
    companies = json.loads(resp.read().decode('utf-8')).get('value', [])
    company_id = next(c['id'] for c in companies if 'peupliers' in c.get('displayName', '').lower())
    comp_name = next(c['name'] for c in companies if 'peupliers' in c.get('displayName', '').lower())

print(f"Société: {comp_name} (ID: {company_id})")

# 2. Récupérer les 3 dernières commandes dans Dev avec leurs lignes
orders_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({company_id})/salesOrders?$top=3&$expand=salesOrderLines"
req_orders = urllib.request.Request(orders_url, headers=headers)
with urllib.request.urlopen(req_orders) as resp:
    orders = json.loads(resp.read().decode('utf-8')).get('value', [])

print(f"\nCommandes trouvées dans Dev ({len(orders)}) :")
for o in orders:
    num = o.get('number')
    cust = o.get('customerName')
    lines = o.get('salesOrderLines', [])
    print(f"\n--- Commande {num} pour {cust} ({len(lines)} lignes) ---")
    for l in lines[:3]:
        print(f"  Line ID: {l.get('id')} | Article: {l.get('description')} | Qte: {l.get('quantity')} | ItemId: {l.get('itemId')}")

# 3. Tester si l'API standard supporte l'expansion ou la sous-ressource itemTrackingLines
if orders and orders[0].get('salesOrderLines'):
    first_order_id = orders[0]['id']
    first_line_id = orders[0]['salesOrderLines'][0]['id']
    
    print(f"\n[Test 1] Test sous-ressource itemTrackingLines sur la ligne {first_line_id}...")
    tracking_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({company_id})/salesOrders({first_order_id})/salesOrderLines({first_line_id})/itemTrackingLines"
    try:
        req_t = urllib.request.Request(tracking_url, headers=headers)
        with urllib.request.urlopen(req_t) as resp:
            t_data = json.loads(resp.read().decode('utf-8'))
            print("  Succès itemTrackingLines API v2.0 :", json.dumps(t_data, indent=2))
    except urllib.error.HTTPError as e:
        print(f"  itemTrackingLines v2.0 non disponible ({e.code}): {e.reason}")

# 4. Tester l'entité Items pour voir les GTINs
print(f"\n[Test 2] Test de l'API Articles pour récupérer les GTINs...")
items_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({company_id})/items?$top=3&$select=id,number,displayName,gtin,itemCategoryCode"
try:
    req_items = urllib.request.Request(items_url, headers=headers)
    with urllib.request.urlopen(req_items) as resp:
        items_data = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"  Articles trouvés ({len(items_data)}) :")
        for it in items_data:
            print(f"   * No: {it.get('number')} | Nom: {it.get('displayName')} | GTIN: {it.get('gtin')}")
except Exception as e:
    print(f"  Erreur Items API: {e}")
