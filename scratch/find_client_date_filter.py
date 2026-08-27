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

comp_id = "46a34776-0a36-ef11-8409-00224838bfdb"
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
# 1. CHERCHER LA DATE DE FILTRAGE DANS LA FICHE CLIENT
# =============================================
print("=" * 70)
print("[1] API v2.0 /customers - Champs client (date de filtrage ?)")
print("=" * 70)

# Tester l'API standard customers
data_cust = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({comp_id})/customers?$top=3",
    "API v2.0 customers"
)
if data_cust and data_cust.get('value'):
    print(f"  Clients trouvés. Champs du premier client :")
    for k, v in data_cust['value'][0].items():
        if k != '@odata.etag':
            print(f"    {k}: {v}")
else:
    print("  API customers non accessible")

# =============================================
# 2. TESTER OData Y18Customer 
# =============================================
print("\n" + "=" * 70)
print("[2] OData Y18Customer - Champs client complets")
print("=" * 70)
data_y18 = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y18Customer?$top=1",
    "Y18Customer"
)
if data_y18 and data_y18.get('value'):
    for k, v in data_y18['value'][0].items():
        if k != '@odata.etag':
            kl = k.lower()
            # Highlight potential date filtering fields
            marker = " <<< DATE ?" if any(x in kl for x in ['date', 'expir', 'filtr', 'dlc', 'shelf', 'warranty']) else ""
            print(f"    {k}: {v}{marker}")
else:
    print("  Y18Customer non accessible")

# =============================================
# 3. CHERCHER SUR UNE COMMANDE SPÉCIFIQUE (salesOrder header)
# =============================================
print("\n" + "=" * 70)
print("[3] Champs complets d'un salesOrder (date de filtrage dans l'en-tête ?)")
print("=" * 70)
data_order = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies({comp_id})/salesOrders?$top=1",
    "salesOrders header"
)
if data_order and data_order.get('value'):
    for k, v in data_order['value'][0].items():
        if k != '@odata.etag' and k != 'salesOrderLines':
            kl = k.lower()
            marker = " <<< DATE ?" if any(x in kl for x in ['date', 'expir', 'filtr', 'dlc', 'shelf', 'warranty']) else ""
            print(f"    {k}: {v}{marker}")

# =============================================
# 4. CHERCHER DANS Fiche_client_Excel (OData)
# =============================================
print("\n" + "=" * 70)
print("[4] OData Fiche_client_Excel - Champs client avec champs custom ?")
print("=" * 70)
data_fce = safe_get(
    f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Fiche_client_Excel?$top=1",
    "Fiche_client_Excel"
)
if data_fce and data_fce.get('value'):
    for k, v in data_fce['value'][0].items():
        if k != '@odata.etag':
            kl = k.lower()
            marker = " <<< DATE ?" if any(x in kl for x in ['date', 'expir', 'filtr', 'dlc', 'shelf', 'warranty']) else ""
            print(f"    {k}: {v}{marker}")
else:
    print("  Fiche_client_Excel non accessible")
