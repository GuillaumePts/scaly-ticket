import json
import unicodedata
import re

def normalize(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower()
    s = re.sub(r'[^a-z0-9]', ' ', s)
    return s

with open('data/parfums_4up.json', 'r', encoding='utf-8') as f:
    parfums_list = json.load(f)

libelles = [
    "6 Yaourt entier Vanille RGF - 2X125G",
    "6 Yaourt entier Abricot RGF - 2X125G",
    "6 Yaourt entier Fraise RGF - 2X125G",
    "6 Yaourt Brasse Nature 140G RGF - 140G",
    "6 Yaourt Brasse Citron 140G RGF - 140G",
    "6 Yaourt Brasse Vanille 140G RGF - 140G",
    "6 Yaourt Brasse Caramel 140G RGF - 140G",
    "6 Yaourt entier Figue RGF - 2X125G",
    "6 Yaourt entier Nature RGF - 2X125G",
    "6 Yaourt nature pot paraffine x4 - 4X125G",
]

for lib in libelles:
    lib_norm = normalize(lib)
    lib_words = set(lib_norm.split())
    
    best_match = None
    max_score = 0
    for p in parfums_list:
        p_norm = normalize(p['nom'])
        p_words = set(p_norm.split())
        
        # Jaccard similarity or intersection size
        score = len(lib_words.intersection(p_words))
        
        # bonus for specific flavors
        for flavor in ['vanille', 'abricot', 'fraise', 'citron', 'caramel', 'figue', 'nature', 'myrtille', 'chocolat', 'cafe']:
            if flavor in p_words and flavor in lib_words:
                score += 5
        
        # bonus for format
        if '2x125' in lib_norm.replace(' ', '') and '2x125' in p_norm.replace(' ', ''):
            score += 3
        if '4x125' in lib_norm.replace(' ', '') and '4x125' in p_norm.replace(' ', ''):
            score += 3
            
        if score > max_score:
            max_score = score
            best_match = p
            
    print(f"{lib[:40]:<40} -> {best_match['nom'] if best_match else 'NONE'} (Score: {max_score})")
