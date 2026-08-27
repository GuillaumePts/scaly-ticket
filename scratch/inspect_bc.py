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

print(f"=== INTERROGATION DES SERVICES WEB DANS L'ENVIRONNEMENT : {env} ===")

# 1. Lister les services ODataV4 au niveau racine
odata_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4"
req = urllib.request.Request(odata_url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        odata_services = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[1] Services ODataV4 racine ({len(odata_services)}) :")
        for s in odata_services:
            name = s.get('name', '')
            url = s.get('url', '')
            print(f"  - {name} -> {url}")
except Exception as e:
    print(f"Erreur ODataV4 racine : {e}")

# 2. Obtenir les sociétés et les services OData de chaque société
companies_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/api/v2.0/companies"
req_comp = urllib.request.Request(companies_url, headers=headers)
try:
    with urllib.request.urlopen(req_comp) as resp:
        companies = json.loads(resp.read().decode('utf-8')).get('value', [])
        print(f"\n[2] Sociétés trouvées ({len(companies)}) :")
        for c in companies:
            disp_name = c.get('displayName')
            name = c.get('name')
            cid = c.get('id')
            print(f"\n=== Société : {disp_name} (name='{name}', id='{cid}') ===")
            
            # Tester ODataV4 par société
            comp_encoded = urllib.parse.quote(name)
            comp_odata_url = f"https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{env}/ODataV4/Company('{comp_encoded}')"
            try:
                req_c_odata = urllib.request.Request(comp_odata_url, headers=headers)
                with urllib.request.urlopen(req_c_odata) as c_resp:
                    c_services = json.loads(c_resp.read().decode('utf-8')).get('value', [])
                    print(f"  Services ODataV4 disponibles ({len(c_services)}) :")
                    for cs in c_services:
                        s_name = cs.get('name', '')
                        s_url = cs.get('url', '')
                        print(f"    * {s_name}")
            except Exception as ce:
                print(f"  Erreur ODataV4 pour la société : {ce}")
except Exception as e:
    print(f"Erreur Companies : {e}")
