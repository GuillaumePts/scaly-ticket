import socket
import time

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data, desc):
    print(f"--- {desc} ---")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux XPML+ESC envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

esc = b"\x1b"
crlf = b"\r\n"

# On suit la structure exacte du driver mais avec les ESC
job = (
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
    esc + b"{D0763,1016,0743|}" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    esc + b"{C|}" + crlf +
    esc + b"{L|}" + crlf +
    esc + b"{PC001;0100,0100,1,1,k,00,B=XPML ESC TEST|}" + crlf +
    # Commande XS du driver avec son ESC
    esc + b"{XS;I,0001,0000C5000|}" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    print("Test 18: XPML Encapsulation WITH ESC characters")
    send_job(job, "XPML + ESC + DRIVER XS")
