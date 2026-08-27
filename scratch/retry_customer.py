import sys
sys.path.insert(0, '.')
import json, urllib.request, urllib.parse, time
from src.bc_client import BusinessCentralClient

bc = BusinessCentralClient()
token = bc.get_access_token()
tid = bc._config['BC_TENANT_ID']
env = 'Dev'
hdr = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
cid = '46a34776-0a36-ef11-8409-00224838bfdb'
cn = urllib.parse.quote('Ferme des Peupliers')

def get(url, label):
    url = urllib.parse.quote(url, safe=":/$%?&=()'#")
    for i in range(3):
        try:
            r = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(r, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if i < 2: time.sleep(2)
            else: print(f'ERREUR {label}: {e}')
    return None

# 1. API v2.0 customers
print('=== [1] API v2.0 /customers ===')
d = get(f'https://api.businesscentral.dynamics.com/v2.0/{tid}/{env}/api/v2.0/companies({cid})/customers?$top=2', 'customers')
if d and d.get('value'):
    for k, v in d['value'][0].items():
        if k != '@odata.etag':
            kl = k.lower()
            tag = ' <<< !' if any(x in kl for x in ['date','expir','filtr','dlc','shelf','warranty','life']) else ''
            print(f'  {k}: {v}{tag}')

# 2. Fiche_client_Excel
print('\n=== [2] OData Fiche_client_Excel ===')
d2 = get(f"https://api.businesscentral.dynamics.com/v2.0/{tid}/{env}/ODataV4/Company('{cn}')/Fiche_client_Excel?$top=1", 'Fiche_client_Excel')
if d2 and d2.get('value'):
    for k, v in d2['value'][0].items():
        if k != '@odata.etag':
            kl = k.lower()
            tag = ' <<< !' if any(x in kl for x in ['date','expir','filtr','dlc','shelf','warranty','life']) else ''
            print(f'  {k}: {v}{tag}')

# 3. Cust_LedgerEntries
print('\n=== [3] OData Cust_LedgerEntries ===')
d3 = get(f"https://api.businesscentral.dynamics.com/v2.0/{tid}/{env}/ODataV4/Company('{cn}')/Cust_LedgerEntries?$top=1", 'Cust_LedgerEntries')
if d3 and d3.get('value'):
    for k, v in d3['value'][0].items():
        if k != '@odata.etag':
            kl = k.lower()
            tag = ' <<< !' if any(x in kl for x in ['date','expir','filtr','dlc','shelf','warranty','life']) else ''
            print(f'  {k}: {v}{tag}')

# 4. Chercher un client SAMADA ou NORMANDIE spécifiquement 
print('\n=== [4] Recherche client SAMADA via API v2.0 ===')
d4 = get(f"https://api.businesscentral.dynamics.com/v2.0/{tid}/{env}/api/v2.0/companies({cid})/customers?$filter=contains(displayName, 'SAMADA')&$top=3", 'SAMADA')
if d4 and d4.get('value'):
    for c in d4['value']:
        print(f"  Client: {c.get('displayName')} (No: {c.get('number')})")
        for k, v in c.items():
            if k != '@odata.etag':
                print(f"    {k}: {v}")
