import socket
import time

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data, desc):
    print(f"--- {desc} ---")
    # On affiche un peu d'hex pour debug
    print(f"Début du flux : {data[:50].hex(' ')}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Perfect Driver' envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

# Construction du job SANS CARACTÈRE ESC (comme vu dans le Hex Dump)
# Et avec les balises XPML exactes.

crlf = b"\r\n"

job = (
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
    b"{D0763,1016,0743|}" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    b"{C|}" + crlf +
    # On ajoute un texte simple en TPCL (sans ESC non plus, pour tester)
    b"{PC001;0100,0100,1,1,k,00,B=DRIVER EMULATION|}" + crlf +
    # La commande XS magique trouvée dans ton fichier
    b"{XS;I,0001,0000C5000|}" + crlf +
    b"<xpml></page></xpml>" +
    # La balise de fin de session
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    print("Test 17: Perfect Driver Emulation (No ESC, XPML Session)")
    send_job(job, "DRIVER CLONE")
