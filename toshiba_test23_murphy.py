import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Murphy' envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

crlf = b"\r\n"

# La Loi de Murphy
murphy = "Tout ce qui est susceptible de mal tourner tournera mal."

# Construction du job en suivant le HEX DUMP du driver à la lettre
job = (
    # 1. Ouverture config
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
    # 2. Commande D (Dimensions) - On utilise les valeurs du driver qui marchent
    b"{D0763,1016,0743|}" + crlf +
    # 3. Fermeture config
    b"<xpml></page></xpml>" +
    # 4. Ouverture Page 1
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    # 5. Commandes TPCL
    b"{C|}" + crlf +
    f"{{PC001;0100,0100,1,1,0,00,B=LOI DE MURPHY:|}}".encode('ascii') + crlf +
    f"{{PC002;0100,0200,1,1,0,00,B={murphy[:40]}|}}".encode('ascii') + crlf +
    f"{{PC003;0100,0300,1,1,0,00,B={murphy[40:]}|}}".encode('ascii') + crlf +
    # 6. Issue (XS)
    b"{XS;I,0001,0000C5000|}" + crlf +
    # 7. Fermeture Page 1
    b"<xpml></page></xpml>" +
    # 8. Fin de session
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    send_job(job)
