import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

esc = b"\x1b"
crlf = b"\r\n"

# Test 29: On utilise les balises du driver MAIS avec du TPCL Standard (ESC)
# pour voir si on peut faire bouger le moteur.
job = (
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
    esc + b"D0763,1016,0743" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    esc + b"C" + crlf +
    # Commande de Feed simple
    esc + b"I" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    print("Test 29: FEED avec ESC à l'intérieur de XPML")
    send_job(job)
