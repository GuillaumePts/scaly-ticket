import sys
import os

# Ajout du dossier source au path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from paletisation_engine import generer_plan_palettisation

produits = [
    {"libelle": "pot paraffine (Test)", "quantite": 135},
    {"libelle": "Yaourt 125g", "quantite": 270},
    {"libelle": "Yaourt 125g fraise", "quantite": 126}
]

print("--- AVEC OPTIMISATION MAX ---")
tours_opt = generer_plan_palettisation(produits, opt_max=True)
for i, t in enumerate(tours_opt):
    print(f"Tour {i+1}: Hauteur {t['hauteur']}cm, Items: {[x['type'] + '(' + str(x['hauteur_cm']) + 'cm)' for x in t['items']]}")

print("\n--- SANS OPTIMISATION MAX ---")
tours_no_opt = generer_plan_palettisation(produits, opt_max=False)
for i, t in enumerate(tours_no_opt):
    print(f"Tour {i+1}: Hauteur {t['hauteur']}cm, Items: {[x['type'] + '(' + str(x['hauteur_cm']) + 'cm)' for x in t['items']]}")
