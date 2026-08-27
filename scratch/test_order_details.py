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

# Société : Ferme des Peupliers
comp_name = "Ferme des Peupliers"
comp_encoded = urllib.parse.quote(comp_name)

print("=== TEST REQUÊTE OData / API LIGNES DE VENTE & ARTICLES ===")

# 1. Tester Y37SalesLineOrder (Lignes de commandes)
url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Y37SalesLineOrder?$top=2"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[1] Y37SalesLineOrder champs disponibles :")
        if data:
            for k, v in data[0].items():
                print(f"  - {k}: {v}")
except Exception as e:
    print(f"Erreur Y37SalesLineOrder : {e}")

# 2. Tester Fiche_article_Excel (Articles avec GTIN / code barre)
url_art = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')/Fiche_article_Excel?$top=2"
req_art = urllib.request.Request(url_art, headers=headers)
try:
    with urllib.request.urlopen(req_art) as resp:
        data_art = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[2] Fiche_article_Excel champs disponibles :")
        if data_art:
            for k, v in data_art[0].items():
                print(f"  - {k}: {v}")
except Exception as e:
    print(f"Erreur Fiche_article_Excel : {e}")
