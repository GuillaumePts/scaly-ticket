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

print("=== RECHERCHE DES TABLES DE STOCK, LOTS ET DATES DANS BUSINESS CENTRAL (GET) ===")

# 1. Tester la table Y32ItemLedgerEntry avec filtre Open eq true (stocks en cours)
url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y32ItemLedgerEntry?$top=10"
print(f"URL: {url}")
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[1] Entrées ItemLedgerEntry trouvées ({len(data)}) :")
        for entry in data:
            print("  --- Entrée ---")
            for k, v in entry.items():
                if k not in ['@odata.etag']:
                    print(f"    {k}: {v}")
except urllib.error.HTTPError as e:
    print(f"Erreur HTTP Y32ItemLedgerEntry ({e.code}): {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Erreur Y32ItemLedgerEntry: {e}")

# 2. Tester si ItemLedgerEntries (page standard) existe
url_ile = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/ItemLedgerEntries?$top=5"
try:
    req_ile = urllib.request.Request(url_ile, headers=headers)
    with urllib.request.urlopen(req_ile) as resp:
        data_ile = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[2] ItemLedgerEntries standard trouvées ({len(data_ile)}) :")
        if data_ile:
            for k, v in data_ile[0].items():
                print(f"    {k}: {v}")
except urllib.error.HTTPError as e:
    print(f"Erreur HTTP ItemLedgerEntries ({e.code}): {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Erreur ItemLedgerEntries: {e}")
