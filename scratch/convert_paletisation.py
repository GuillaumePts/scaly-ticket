import pandas as pd
import json
import os

file_path = r'C:\projetPro\scaly-ticket\paletisation\Annexe logistique 1.xlsx'
out_path = r'C:\projetPro\scaly-ticket\paletisation\config_paletisation.json'

xl = pd.ExcelFile(file_path)

def safe_float(val):
    if pd.isna(val) or str(val).strip() in ['', '?']:
        return None
    try:
        return float(str(val).replace(',', '.'))
    except ValueError:
        return None

# 1. Parsing Articles
df_articles = xl.parse('Articles')
articles = []
for _, row in df_articles.iterrows():
    n_val = row.iloc[0]
    if pd.isna(n_val) or str(n_val).strip() == '':
        continue
    articles.append({
        "reference": str(n_val).strip(),
        "description": str(row.iloc[1]).strip(),
        "unite_base": str(row.iloc[2]).strip(),
        "poids_unitaire_g": safe_float(row.iloc[3])
    })

# 2. Parsing Emballages
df_emb = xl.parse('Emballages')
emballages = []
for _, row in df_emb.iterrows():
    nom = str(row.iloc[0]).strip()
    if nom == 'nan' or nom == 'Désignation' or nom == 'Dsignation':
        continue
    emballages.append({
        "nom": nom,
        "poids_g": safe_float(row.iloc[1]),
        "dimensions_cm": str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else None,
        "caracteristiques": str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else None
    })

# 3. Manually adding the constraints specified by the user
contraintes_globales = {
    "hauteur_max_palette_cm": 220,
    "poids_max_palette_kg": None, # A demander
    "clients_speciaux": {
        "cremlog": {
            "un_parfum_par_palette": True
        },
        "cremcentre": {
            "un_parfum_par_palette": True
        }
    }
}

regles_empilement = {
    "carton 48 pots": {
        "colis_par_couche": 9,
        "couches_max": 8,
        "total_colis": 72
    },
    "carton 6x140g": {
        "colis_par_couche": 36,
        "couches_max": 10,
        "total_colis": 360
    },
    "carton x24": {
        "colis_par_couche": 9,
        "couches_max": 15,
        "total_colis": 135
    },
    "carton x12": {
        "colis_par_couche": 18,
        "couches_max": 10,
        "total_colis": 180
    },
    "skyr": {
        "colis_par_couche": 13,
        "couches_max": 10,
        "total_colis": 130
    }
}

data = {
    "contraintes_globales": contraintes_globales,
    "regles_empilement": regles_empilement,
    "articles": articles,
    "emballages": emballages
}

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("JSON généré avec succès dans :", out_path)
