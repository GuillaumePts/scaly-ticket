import json
import os
from collections import defaultdict
import math

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'paletisation', 'config_paletisation.json')
POIDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'paletisation', 'poids_produits.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

POIDS_DB = {}
try:
    with open(POIDS_PATH, 'r', encoding='utf-8') as f:
        POIDS_DB = json.load(f)
except FileNotFoundError:
    pass

EPAISSEUR_PALETTE_VIDE = config['contraintes_globales']['epaisseur_palette_vide_cm']
HAUTEUR_MAX_TOUR = config['contraintes_globales']['hauteur_max_palette_cm']

# Hauteur théorique d'une palette "pleine" (hors bois). 
# Pour l'instant on va faire une approximation à 100cm par palette pleine pour tester le gerbage, 
# puisqu'on n'a pas la hauteur exacte des cartons dans le json de base (à affiner plus tard).
HAUTEUR_PALETTE_PLEINE_CM = 100 

def determiner_type_colis(libelle):
    lib_lower = libelle.lower()
    if 'paraffine' in lib_lower:
        return 'pot paraffine', 'C'
    elif 'skyr' in lib_lower:
        return 'skyr', 'B'
    elif '140g' in lib_lower:
        return 'carton 6x140g', 'B'
    elif '2x125g' in lib_lower or '4x125g' in lib_lower or '125g' in lib_lower:
        return 'carton x12', 'A'
    return 'inconnu', 'A'

class Tour:
    def __init__(self):
        self.items = []
        self.hauteur = 0
        self.poids_kg = 0 # Le poids des palettes EPAL sera ajouté à chaque item
        self.familles = set()
        self.has_fragile = False
        
        self.has_A_full = False
        self.has_B_full = False
        self.has_A_chute = False
        self.has_B_chute = False

    def can_add(self, item, opt_max=False):
        if self.hauteur + item['hauteur_cm'] + EPAISSEUR_PALETTE_VIDE > HAUTEUR_MAX_TOUR:
            return False
        if self.has_fragile and item['fragile']:
            return False
            
        if not opt_max:
            item_fam = item['famille']
            item_pleine = item.get('pleine', False)
            
            is_A_full = (item_fam == 'A' and item_pleine)
            is_B_full = (item_fam == 'B' and item_pleine)
            is_A_chute = (item_fam == 'A' and not item_pleine)
            is_B_chute = (item_fam == 'B' and not item_pleine)
            
            if is_A_full:
                if self.has_B_full:
                    return False
            elif is_B_full:
                if self.has_A_full:
                    return False
                    
        return True

    def add(self, item):
        self.items.append(item)
        self.hauteur += item['hauteur_cm'] + EPAISSEUR_PALETTE_VIDE
        self.poids_kg += item.get('poids_kg', 0) + 25.0 # Chaque item (palette logique) a sa propre base en bois (25kg)
        self.familles.add(item['famille'])
        if item['fragile']:
            self.has_fragile = True
            
        item_fam = item['famille']
        item_pleine = item.get('pleine', False)
        if item_fam == 'A':
            if item_pleine:
                self.has_A_full = True
            else:
                self.has_A_chute = True
        elif item_fam == 'B':
            if item_pleine:
                self.has_B_full = True
            else:
                self.has_B_chute = True

    def get_items_sorted(self):
        # Les items fragiles doivent toujours être au sommet (à la fin de la liste)
        return sorted(self.items, key=lambda x: x['fragile'])
        
    def to_dict(self):
        return {
            "hauteur": self.hauteur,
            "poids_kg": round(self.poids_kg, 2),
            "familles": sorted(list(self.familles)),
            "items": self.get_items_sorted()
        }

def get_poids_unitaire(libelle, type_colis):
    # Match exact
    if libelle in POIDS_DB:
        return POIDS_DB[libelle]
        
    # Match partiel / heuristique
    lib_lower = libelle.lower()
    for k, v in POIDS_DB.items():
        if k.lower() in lib_lower or lib_lower in k.lower():
            return v
            
    # Fallback par famille
    if type_colis == 'carton x12' or type_colis == 'carton x24' or type_colis == 'plateau x6':
        return 0.1985
    elif type_colis == 'brassé 140g':
        return 0.2255
    elif type_colis == 'pot paraffine':
        return 0.1353
    elif type_colis == 'skyr':
        return 0.500
    return 0.2

def creer_palettes_logiques(produits, opt_max=False):
    palettes = []
    chutes = []
    
    for item in produits:
        libelle = item['libelle']
        qte = item['quantite']
        if qte <= 0:
            continue
            
        type_colis, famille = determiner_type_colis(libelle)
        poids_pot_kg = get_poids_unitaire(libelle, type_colis)
        
        # Récupération de la règle
        regle = config['regles_empilement'].get(type_colis)
        if not regle or regle.get('total_colis', 0) == 0:
            # Fallback
            max_colis = 135 
            fragile = True if type_colis == 'pot paraffine' else False
            colis_par_couche = 9
            hauteur_carton = 7.0 if type_colis == 'pot paraffine' else 14.5
            pots_par_colis = 12
        else:
            max_colis = regle['total_colis']
            fragile = regle.get('fragile_top_only', False)
            colis_par_couche = regle.get('colis_par_couche', 1)
            hauteur_carton = regle.get('hauteur_carton_cm', 14.5)
            pots_par_colis = regle.get('pots_par_colis', 12)
            
        poids_colis_kg = poids_pot_kg * pots_par_colis + 0.15 # 0.15kg = poids du carton vide approximatif

            
        # Overrides dynamiques
        if type_colis == 'carton x12':
            if opt_max:
                max_colis = 15 * colis_par_couche # 270
            
        nb_palettes_pleines = qte // max_colis
        reste = qte % max_colis
        
        # Hauteur d'une palette pleine
        couches_pleine = max_colis // colis_par_couche if colis_par_couche > 0 else 0
        hauteur_pleine = couches_pleine * hauteur_carton
        
        for _ in range(nb_palettes_pleines):
            palettes.append({
                "libelle": libelle,
                "famille": famille,
                "type": type_colis,
                "qte": max_colis,
                "couches": couches_pleine,
                "colis_par_couche": colis_par_couche,
                "pleine": True,
                "fragile": fragile,
                "hauteur_cm": hauteur_pleine,
                "poids_kg": round(max_colis * poids_colis_kg, 2)
            })
            
        if reste > 0:
            couches_chute = reste // colis_par_couche if colis_par_couche > 0 else 1
            # Arrondi supérieur si reste
            if colis_par_couche > 0 and reste % colis_par_couche > 0:
                couches_chute += 1
                
            hauteur_chute = couches_chute * hauteur_carton
            
            chutes.append({
                "libelle": libelle,
                "famille": famille,
                "type": type_colis,
                "qte": reste,
                "couches": couches_chute,
                "colis_par_couche": colis_par_couche,
                "pleine": False,
                "fragile": fragile,
                "hauteur_cm": hauteur_chute,
                "poids_kg": round(reste * poids_colis_kg, 2)
            })
            
    return palettes, chutes

def assembler_tours(palettes, chutes, opt_max=False):
    tous_les_items = palettes + chutes
    
    # FFD Global sur TOUS les items.
    # La méthode can_add gère l'isolation des familles intelligemment si opt_max=False
    items_tries = sorted(tous_les_items, key=lambda x: x['hauteur_cm'], reverse=True)
    tours = []
    
    for item in items_tries:
        placed = False
        for tour in tours:
            if tour.can_add(item, opt_max=opt_max):
                tour.add(item)
                placed = True
                break
        if not placed:
            nt = Tour()
            nt.add(item)
            tours.append(nt)
            
    # Tri interne pour que les fragiles soient physiquement en haut (donc à la fin de la liste)
    for t in tours:
        t.items.sort(key=lambda x: 1 if x['fragile'] else 0)
        
    return tours

def generer_plan_palettisation(produits, opt_max=False, client=""):
    """
    produits = [{"libelle": "...", "quantite": 100}, ...]
    retourne un json de tours
    """
    client_upper = client.upper() if client else ""
    if "SAMADA" in client_upper:
        return generer_plan_palettisation_samada(produits)
        
    palettes_pleines, chutes = creer_palettes_logiques(produits, opt_max=opt_max)
    tours = assembler_tours(palettes_pleines, chutes, opt_max=opt_max)
    return [t.to_dict() for t in tours]

def generer_plan_palettisation_samada(produits):
    groupes = {'brasse': [], 'classique': []}
    for item in produits:
        libelle = item['libelle']
        qte = item['quantite']
        if qte <= 0:
            continue
        lib_lower = libelle.lower()
        if 'brasse' in lib_lower or 'brassé' in lib_lower or '140g' in lib_lower:
            groupes['brasse'].append(item)
        elif '125g' in lib_lower or 'x12' in lib_lower:
            groupes['classique'].append(item)
        else:
            groupes['classique'].append(item)
            
    tours = []
    logical_pallets = []
    
    for type_groupe, items in groupes.items():
        if not items:
            continue
            
        colis_par_couche = 36 if type_groupe == 'brasse' else 18
        max_colis_par_palette = 7 * colis_par_couche
        base_qty = 4 * colis_par_couche
        
        total_qte = sum(i['quantite'] for i in items)
        
        pallets_sizes = []
        rem = total_qte
        while rem > 0:
            if rem <= max_colis_par_palette:
                pallets_sizes.append(rem)
                rem = 0
            else:
                if rem > max_colis_par_palette and rem < max_colis_par_palette + base_qty:
                    pallets_sizes.append(base_qty)
                    rem -= base_qty
                else:
                    pallets_sizes.append(max_colis_par_palette)
                    rem -= max_colis_par_palette
                    
        item_idx = 0
        rem_item_qte = items[item_idx]['quantite'] if items else 0
        
        for size in pallets_sizes:
            cols = 4 if type_groupe == 'brasse' else 3
            rows = 9 if type_groupe == 'brasse' else 6
            P = rows * cols
            
            base_pile = size // P
            extra = size % P
            
            grid = []
            for r in range(rows):
                row_data = []
                for c in range(cols):
                    pile_idx = r * cols + c
                    pile_cap = base_pile + (1 if pile_idx < extra else 0)
                    
                    pile_contents = []
                    rem_pile_cap = pile_cap
                    
                    while rem_pile_cap > 0 and item_idx < len(items):
                        take = min(rem_pile_cap, rem_item_qte)
                        if take > 0:
                            if pile_contents and pile_contents[-1]['libelle'] == items[item_idx]['libelle']:
                                pile_contents[-1]['qte'] += take
                            else:
                                pile_contents.append({
                                    "libelle": items[item_idx]['libelle'],
                                    "qte": take
                                })
                            rem_pile_cap -= take
                            rem_item_qte -= take
                            
                        if rem_item_qte == 0:
                            item_idx += 1
                            if item_idx < len(items):
                                rem_item_qte = items[item_idx]['quantite']
                                
                    row_data.append({
                        "total_boxes": pile_cap,
                        "contents": pile_contents
                    })
                grid.append(row_data)
                
            couches_eff = math.ceil(size / colis_par_couche)
            hauteur = couches_eff * 14.5
            
            # Create a logical pallet object
            logical_pallet = {
                "is_samada": True,
                "type_colis": type_groupe,
                "qte": size,
                "couches": couches_eff,
                "grid": grid,
                "libelle": f"Palette {type_groupe.capitalize()} (SAMADA)",
                "famille": "SAMADA",
                "hauteur_cm": hauteur,
                "fragile": False,
                "pleine": size == max_colis_par_palette,
                "poids_kg": size * 0.25
            }
            logical_pallets.append(logical_pallet)
            
    # Now stack logical pallets into tours (gerbage)
    tours = []
    for pal in logical_pallets:
        placed = False
        for tour in tours:
            # Check if it fits (height + epaisseur pallet)
            if tour['hauteur'] + pal['hauteur_cm'] + 15 <= 212: # 212 = HAUTEUR_MAX_TOUR
                tour['items'].append(pal)
                tour['hauteur'] += pal['hauteur_cm'] + 15
                tour['poids_kg'] += pal['poids_kg'] + 25
                placed = True
                break
        if not placed:
            tours.append({
                "is_samada": True,
                "items": [pal],
                "hauteur": pal['hauteur_cm'],
                "poids_kg": pal['poids_kg'] + 25,
                "familles": ["SAMADA"]
            })
            
    return tours
