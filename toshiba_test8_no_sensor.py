import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

esc = b"\x1b"

# Test 8: Print complet SANS capteur
# Si le capteur est mal calibré, l'imprimante attend indéfiniment un gap.
# En mettant le paramètre p4 à 0 (No sensor), elle doit imprimer immédiatement.
job = (
    esc + b"{D0300,0800,0300|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    esc + b"{PC001;0100,0100,1,1,k,00,B=TEST 8 NO SENSOR|}" +
    esc + b"{XS;0001,0004,0000,0,0,0,0,0|}"
)

if __name__ == "__main__":
    print("Test 8: Hybride Print (Sensor 0 - No Sensor)")
    send_job(job)
