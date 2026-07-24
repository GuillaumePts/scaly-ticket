import json
import os
from collections import defaultdict

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'paletisation', 'config_paletisation.json')

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

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
        self.familles = set()
        self.has_fragile = False

    def can_add(self, item):
        if self.hauteur + item['hauteur_cm'] + EPAISSEUR_PALETTE_VIDE > HAUTEUR_MAX_TOUR:
            return False
        if self.has_fragile and item['fragile']:
            return False
        return True

    def add(self, item):
        self.items.append(item)
        self.hauteur += item['hauteur_cm'] + EPAISSEUR_PALETTE_VIDE
        self.familles.add(item['famille'])
        if item['fragile']:
            self.has_fragile = True

    def merge(self, other_tour):
        if self.hauteur + other_tour.hauteur > HAUTEUR_MAX_TOUR:
            return False
        if self.has_fragile and other_tour.has_fragile:
            return False
        
        self.items.extend(other_tour.items)
        self.hauteur += other_tour.hauteur
        self.familles.update(other_tour.familles)
        self.has_fragile = self.has_fragile or other_tour.has_fragile
        return True

    def get_items_sorted(self):
        # Les items fragiles doivent toujours être au sommet (à la fin de la liste)
        return sorted(self.items, key=lambda x: x['fragile'])
        
    def to_dict(self):
        return {
            "hauteur": self.hauteur,
            "familles": sorted(list(self.familles)),
            "items": self.get_items_sorted()
        }

def creer_palettes_logiques(produits):
    palettes = []
    chutes = []
    
    for item in produits:
        libelle = item['libelle']
        qte = item['quantite']
        if qte <= 0:
            continue
            
        type_colis, famille = determiner_type_colis(libelle)
        
        # Récupération de la règle
        regle = config['regles_empilement'].get(type_colis)
        if not regle or regle.get('total_colis', 0) == 0:
            # Fallback
            max_colis = 135 
            fragile = True if type_colis == 'pot paraffine' else False
        else:
            max_colis = regle['total_colis']
            fragile = regle.get('fragile_top_only', False)
            
        nb_palettes_pleines = qte // max_colis
        reste = qte % max_colis
        
        for _ in range(nb_palettes_pleines):
            palettes.append({
                "libelle": libelle,
                "famille": famille,
                "type": type_colis,
                "qte": max_colis,
                "pleine": True,
                "fragile": fragile,
                "hauteur_cm": HAUTEUR_PALETTE_PLEINE_CM
            })
            
        if reste > 0:
            chutes.append({
                "libelle": libelle,
                "famille": famille,
                "type": type_colis,
                "qte": reste,
                "pleine": False,
                "fragile": fragile,
                # Hauteur proportionnelle stricte (ex: 18/180 = 10% de 100cm = 10cm)
                "hauteur_cm": max(5, int(HAUTEUR_PALETTE_PLEINE_CM * (reste / max_colis)))
            })
            
    return palettes, chutes

def assembler_tours(palettes, chutes, opt_max=False):
    tous_les_items = palettes + chutes
    
    if opt_max:
        # FFD Global sans tenir compte des familles
        solides = sorted([i for i in tous_les_items if not i['fragile']], key=lambda x: x['hauteur_cm'], reverse=True)
        fragiles = sorted([i for i in tous_les_items if i['fragile']], key=lambda x: x['hauteur_cm'], reverse=True)
        
        tours_finales = []
        for item in solides + fragiles:
            placé = False
            for t in tours_finales:
                if t.can_add(item):
                    t.add(item)
                    placé = True
                    break
            if not placé:
                nt = Tour()
                nt.add(item)
                tours_finales.append(nt)
        return tours_finales
        
    # Etape 1 : Grouper par famille
    items_par_famille = defaultdict(list)
    for item in tous_les_items:
        items_par_famille[item['famille']].append(item)
        
    tours_pures = []
    
    # Etape 2 : FFD Bin Packing intra-famille
    for famille, items in items_par_famille.items():
        solides = sorted([i for i in items if not i['fragile']], key=lambda x: x['hauteur_cm'], reverse=True)
        fragiles = sorted([i for i in items if i['fragile']], key=lambda x: x['hauteur_cm'], reverse=True)
        
        tours_locales = []
        
        # Placer les solides
        for item in solides:
            placé = False
            for t in tours_locales:
                if t.can_add(item):
                    t.add(item)
                    placé = True
                    break
            if not placé:
                nouvelle_tour = Tour()
                nouvelle_tour.add(item)
                tours_locales.append(nouvelle_tour)
                
        # Placer les fragiles
        for item in fragiles:
            placé = False
            for t in tours_locales:
                if t.can_add(item):
                    t.add(item)
                    placé = True
                    break
            if not placé:
                nouvelle_tour = Tour()
                nouvelle_tour.add(item)
                tours_locales.append(nouvelle_tour)
                
        tours_pures.extend(tours_locales)
        
    # Etape 3 : FFD Bin Merging inter-familles (Optimisation des chutes et espaces vides)
    # On trie les tours pures par hauteur décroissante
    tours_pures.sort(key=lambda x: x.hauteur, reverse=True)
    
    tours_finales = []
    for tour in tours_pures:
        fusionné = False
        for tf in tours_finales:
            if tf.merge(tour):
                fusionné = True
                break
        if not fusionné:
            tours_finales.append(tour)
            
    return tours_finales

def generer_plan_palettisation(produits, opt_max=False):
    """
    produits = [{"libelle": "...", "quantite": 100}, ...]
    retourne un json de tours
    """
    palettes_pleines, chutes = creer_palettes_logiques(produits)
    tours = assembler_tours(palettes_pleines, chutes, opt_max=opt_max)
    return [t.to_dict() for t in tours]
