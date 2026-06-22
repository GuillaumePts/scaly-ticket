import socket
import sys

def imprimer_etiquette_toshiba(ip_imprimante, port=9100):
    # Definition du flux XPML/TPCL-XML propre à Toshiba
    flux_xml = """<?xml version="1.0" encoding="utf-8"?>
<labels version="1.0">
    <setup>
        <size width="100" height="150" unit="mm"/>
        <speed>4</speed>
        <sensor>transmissive</sensor>
        <quantity>1</quantity>
    </setup>
    <page>
        <text x="15" y="20" font="0" width="1.5" height="1.5">
            <data><![CDATA[STATUS: OK]]></data>
        </text>
        <barcode x="15" y="40" type="code128" height="15" printable="true">
            <data><![CDATA[B-FV4-TEST]]></data>
        </barcode>
    </page>
</labels>\r\n"""

    print(f"Connexion à la Toshiba sur {ip_imprimante}:{port}...")
    
    try:
        # Ouverture du socket TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Timeout de 5 secondes pour ne pas bloquer ton application si l'imprimante est hors-ligne
            s.settimeout(5) 
            s.connect((ip_imprimante, port))
            
            # Encodage strict en UTF-8 (ou ASCII selon la config de la carte d'impression)
            s.sendall(flux_xml.encode('utf-8'))
            
            print("🚀 Flux envoyé ! L'imprimante devrait traiter le job.")
            
    except socket.timeout:
        print("❌ Erreur : Impossible de joindre l'imprimante (Timeout). Vérifie le réseau.", file=sys.stderr)
    except Exception as e:
        print(f"❌ Erreur critique lors de l'envoi : {e}", file=sys.stderr)

if __name__ == "__main__":
    # Ton IP cible
    TOSHIBA_IP = "200.200.129.82"
    TOSHIBA_PORT = 9100
    
    imprimer_etiquette_toshiba(TOSHIBA_IP, TOSHIBA_PORT)