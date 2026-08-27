import sys
sys.path.insert(0, '.')
import json
from src.bc_client import BusinessCentralClient

bc = BusinessCentralClient()
print("=== CHECKUP COMMANDE 266124 DANS DEV ===")

# 1. Requête brute sur Business Central
token = bc.get_access_token()
tenant_id = bc._config['BC_TENANT_ID']
env = 'Dev'
company_id = '46a34776-0a36-ef11-8409-00224838bfdb'

order_res = bc._query_orders(tenant_id, env, company_id, token, "contains(number, '266124')")
if not order_res:
    order_res = bc._query_orders(tenant_id, env, company_id, token, "contains(number, '266')")

print(f"Commandes trouvées : {len(order_res)}")
for o in order_res:
    print(f"\nNuméro: {o.get('number')}")
    print(f"Client: {o.get('customerName')}")
    print(f"orderDate: {o.get('orderDate')}")
    print(f"requestedDeliveryDate: {o.get('requestedDeliveryDate')}")
    print(f"postingDate: {o.get('postingDate')}")
    print(f"lastModifiedDateTime: {o.get('lastModifiedDateTime')}")
    print(f"Lignes ({len(o.get('salesOrderLines', []))}):")
    for l in o.get('salesOrderLines', []):
        print(f"  * {l.get('description')} | Qte: {l.get('quantity')} | ShipmentDate: {l.get('shipmentDate')} | PlannedDeliveryDate: {l.get('plannedDeliveryDate')}")

# 2. Ce que retourne fetch_sales_order actuel
print("\n=== RÉSULTAT ACTUEL DE fetch_sales_order ===")
res = bc.fetch_sales_order("266124")
print(json.dumps(res, indent=2, ensure_ascii=False))
