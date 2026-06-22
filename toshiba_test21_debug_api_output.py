from src.zpl_engine import ZPLEngine
from src.models import TicketData

def debug_api_output():
    engine = ZPLEngine(dpi=203)
    data = TicketData(
        libelle="TEST PRODUIT",
        client="CLIENT TEST",
        gtin="03412345678901",
        date_expiration="260612",
        lot="L260612",
        num_lot_display="L260612",
        quantite=3,
        commande="123456",
        date_livraison="2026-06-12"
    )
    
    flux = engine.generate_ticket_tpcl(data)
    
    print("--- FLUX GÉNÉRÉ PAR L'API ---")
    print(flux)
    print("--- HEXADÉCIMAL ---")
    print(flux.encode('latin-1').hex(' '))
    
    with open("api_output_debug.bin", "wb") as f:
        f.write(flux.encode('latin-1'))
    print("\nFichier 'api_output_debug.bin' créé pour comparaison.")

if __name__ == "__main__":
    debug_api_output()
