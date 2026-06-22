import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Murphy Binaire' envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

# Construction chirurgicale du job
# On utilise les octets exacts du driver pour les balises
header_config = b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>{D0763,1016,0743|}\r\n<xpml></page></xpml>"
header_job = b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>{C|}\r\n"

# Corps du texte (Loi de Murphy)
# On tente SANS ESC d'abord, car le driver n'en avait pas au début.
murphy_text = (
    b"{PC001;0100,0100,1,1,k,00,B=LOI DE MURPHY:|}\r\n" +
    b"{PC002;0100,0200,1,1,k,00,B=Tout ce qui peut mal tourner,|}\r\n" +
    b"{PC003;0100,0300,1,1,k,00,B=tournera mal. (Murphy)|}\r\n"
)

# Sortie (XS) et Fin
# On utilise la commande XS du driver qui a marché : {XS;I,0001,0000C5000|}
footer = b"{XS;I,0001,0000C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>"

job = header_config + header_job + murphy_text + footer

if __name__ == "__main__":
    send_job(job)
