import csv
import json
import math
from collections import defaultdict

# Chargement de la configuration
with open(r'C:\projetPro\scaly-ticket\paletisation\config_paletisation.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

EPAISSEUR_PALETTE_VIDE = config['contraintes_globales']['epaisseur_palette_vide_cm']
HAUTEUR_MAX_TOUR = config['contraintes_globales']['hauteur_max_palette_cm']

# Hauteur théorique d'une palette "pleine" (hors bois). 
# Pour l'instant on va faire une approximation à 150cm par palette pleine pour tester le gerbage, 
# puisqu'on n'a pas la hauteur exacte des cartons dans le json de base (à affiner plus tard).
HAUTEUR_PALETTE_PLEINE_CM = 100 

def determiner_type_colis(libelle):
    lib_lower = libelle.lower()
    if 'paraffine' in lib_lower:
        return 'paraffine', 'C'
    elif 'skyr' in lib_lower:
        return 'skyr', 'B'
    elif '140g' in lib_lower:
        return 'carton 6x140g', 'B'
    elif '2x125g' in lib_lower or '4x125g' in lib_lower or '125g' in lib_lower:
        # Simplification: on suppose carton x24 pour le 125g par defaut si on n'a pas plus d'info
        # A voir avec le client comment differencier x12, x24, 48 pots
        return 'carton x24', 'A'
    return 'inconnu', 'A'

def parse_commande(file_path):
    produits = defaultdict(int)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if not row.get('Libelle') or not row.get('Quantite'):
                continue
            libelle = row['Libelle']
            quantite = int(row['Quantite'])
            produits[libelle] += quantite
    return produits

def creer_palettes_logiques(produits):
    palettes = []
    chutes = []
    
    for libelle, qte in produits.items():
        type_colis, famille = determiner_type_colis(libelle)
        
        # Récupération de la règle
        regle = config['regles_empilement'].get(type_colis)
        if not regle or regle.get('total_colis', 0) == 0:
            # Fallback temporaire pour paraffine
            max_colis = 135 
            fragile = True if type_colis == 'paraffine' else False
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
                # Hauteur proportionnelle pour la chute (approximation)
                "hauteur_cm": max(20, int(HAUTEUR_PALETTE_PLEINE_CM * (reste / max_colis)))
            })
            
    return palettes, chutes

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

def assembler_tours(palettes, chutes):
    tous_les_items = palettes + chutes
    
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

def afficher_resultat(tours):
    print("=== PLAN DE PALETTISATION OPTIMISÉ ===\n")
    print(f"Nombre total de tours (palettes au sol) : {len(tours)}\n")
    for i, tour in enumerate(tours, 1):
        familles_str = ','.join(sorted(list(tour.familles)))
        print(f"TOUR {i} - Hauteur estimée: {tour.hauteur}cm - Familles: {familles_str}")
        items_tries = tour.get_items_sorted()
        for j, pal in enumerate(items_tries, 1):
            etat = "PLEINE" if pal['pleine'] else "CHUTE"
            frag = " (FRAGILE)" if pal['fragile'] else ""
            print(f"  |- Niveau {j}: {pal['qte']} x {pal['libelle']} [{etat}]{frag}")
        print("")

if __name__ == '__main__':
    fichier_cmd = r'C:\projetPro\scaly-ticket\commande.txt'
    prods = parse_commande(fichier_cmd)
    palettes_pleines, chutes = creer_palettes_logiques(prods)
    tours = assembler_tours(palettes_pleines, chutes)
    afficher_resultat(tours)
