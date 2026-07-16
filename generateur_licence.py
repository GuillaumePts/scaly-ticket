import json
from src.licence import generate_signature

def main():
    print("="*50)
    print("   GÉNÉRATEUR DE LICENCE SCALY-TICKET (ADMIN)   ")
    print("="*50)
    print("Attention: Ce script est pour vous uniquement. Ne le donnez jamais au client.\n")
    
    machine_id = input("Entrez l'identifiant matériel du client (Machine ID / MAC) : ").strip()
    expiration_date = input("Entrez la date d'expiration (Format: YYYY-MM-DD, ex: 2027-01-01) : ").strip()
    
    if not machine_id or not expiration_date:
        print("Erreur: Les champs ne peuvent pas être vides.")
        return
        
    signature = generate_signature(machine_id, expiration_date)
    
    licence_data = {
        "machine_id": machine_id,
        "expiration": expiration_date,
        "signature": signature
    }
    
    # Sauvegarde le fichier généré
    with open("licence.key", "w", encoding="utf-8") as f:
        json.dump(licence_data, f, indent=4)
        
    print(f"\n[SUCCÈS] Le fichier 'licence.key' a été généré avec succès.")
    print("Instructions :")
    print("1. Copiez ce fichier 'licence.key'.")
    print("2. Collez-le dans le dossier du client, juste à côté de 'ScalyTicket.exe'.")
    print("3. C'est tout !")

if __name__ == "__main__":
    main()
