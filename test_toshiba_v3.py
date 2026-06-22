import socket
import time

IP_TOSHIBA = "200.200.129.82"
PORT = 9100
esc = b"\x1b"

def send(data, desc):
    print(f"Envoi : {desc}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("OK.")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    # 1. Test FEED (Mouvement pur) en mode Hybride
    # La commande 'f' est souvent utilisée pour avancer d'une étiquette.
    feed_job = esc + b"{f0001|}"
    send(feed_job, "FEED 1 label (Hybrid)")
    
    time.sleep(2)

    # 2. Test PRINT (XS) minimaliste
    # Parfois en hybride, on n'a pas besoin de tous les paramètres
    print_min = (
        esc + b"{D0400,0800,0400|}" +
        esc + b"{C|}" +
        esc + b"{L|}" +
        esc + b"{PC001;0100,0100,1,1,k,00,B=TEST MIN|}" +
        esc + b"{XS;0001,0004,0000,1,0,0,0,0|}"
    )
    send(print_min, "PRINT Minimal (Hybrid)")

    time.sleep(2)

    # 3. Test XS sans point-virgule (Certaines versions TPCL)
    print_no_semi = (
        esc + b"{D0400,0800,0400|}" +
        esc + b"{C|}" +
        esc + b"{L|}" +
        esc + b"{PC001;0100,0100,1,1,k,00,B=TEST NO SEMI|}" +
        esc + b"{XS0001,0004,0000,1,0,0,0,0|}"
    )
    send(print_no_semi, "PRINT No Semicolon (Hybrid)")
