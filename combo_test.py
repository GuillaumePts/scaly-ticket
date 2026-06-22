import socket
import time

host = "200.200.129.82"
port = 9100
esc = b"\x1b"

def send(name, data):
    print(f"--- Envoi Test {name} ---")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((host, port))
            s.sendall(data)
            print(f"Test {name} envoyé.")
    except Exception as e:
        print(f"Erreur Test {name}: {e}")

# 1. ZPL (Zebra) - Classique
zpl = b"^XA^FO50,50^A0N,50,50^FD1-TEST ZPL^FS^XZ"

# 2. TPCL (Toshiba) - Avec CR/LF stricts et Reset
tpcl_standard = esc + b"AX" + esc + b"C" + esc + b"L" + \
                esc + b"PC001;0100,0100,1,1,k,00,B=2-TEST TPCL STD|" + \
                esc + b"XS" + esc + b"I\r\n"

# 3. TPCL (Toshiba) - Syntaxe Alternative (PC000 et sans AX)
tpcl_alt = esc + b"C" + esc + b"L" + \
           esc + b"PC000;0100,0150,1,1,k,00,B=3-TEST TPCL ALT|" + \
           esc + b"XS" + esc + b"I\r\n"

if __name__ == "__main__":
    print("DEMARRAGE DU COMBO TEST (Attendez 10 secondes avant d'aller voir)")
    
    send("ZPL", zpl)
    time.sleep(3)
    
    send("TPCL STD", tpcl_standard)
    time.sleep(3)
    
    send("TPCL ALT", tpcl_alt)
    
    print("FIN DU COMBO. Vérifiez si l'imprimante a sorti une ou plusieurs étiquettes.")
