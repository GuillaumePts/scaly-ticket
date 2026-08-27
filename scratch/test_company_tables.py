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

# ID exact de la société "Ferme des Peupliers"
comp_id = "46a34776-0a36-ef11-8409-00224838bfdb"
comp_name = "Ferme des Peupliers"
comp_encoded = urllib.parse.quote(comp_name)

print(f"=== TEST SUR LA SOCIÉTÉ EXACTE : {comp_name} ({comp_id}) ===")

# 1. Récupérer les 3 dernières commandes de "Ferme des Peupliers"
orders_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({comp_id})/salesOrders?$top=3&$expand=salesOrderLines"
req_orders = urllib.request.Request(orders_url, headers=headers)
try:
    with urllib.request.urlopen(req_orders) as resp:
        orders = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"Commandes trouvées ({len(orders)}) :")
        for o in orders:
            print(f"  * Commande {o.get('number')} - Client: {o.get('customerName')} - Lignes: {len(o.get('salesOrderLines', []))}")
            for l in o.get('salesOrderLines', [])[:3]:
                print(f"      Article: {l.get('description')} | Qte: {l.get('quantity')}")
except Exception as e:
    print(f"Erreur salesOrders : {e}")

# 2. Tester les écritures d'articles (ItemLedgerEntries / Y32ItemLedgerEntry)
print("\n[Test OData] Y32ItemLedgerEntry (Écritures comptables articles avec lots et DLC) :")
url_ile = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y32ItemLedgerEntry?$top=3"
try:
    req_ile = urllib.request.Request(url_ile, headers=headers)
    with urllib.request.urlopen(req_ile) as resp:
        ile_data = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"  Entrées trouvées ({len(ile_data)}) :")
        if ile_data:
            for k, v in ile_data[0].items():
                print(f"    - {k}: {v}")
except Exception as e:
    print(f"  Erreur Y32ItemLedgerEntry : {e}")
