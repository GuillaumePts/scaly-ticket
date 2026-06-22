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

# Test 7: Feed uniquement en mode Hybride
# {IB; quantité, capteur, coupe |}
# 0001 : 1 etiquette
# 0 : Pas de capteur (force l'avance quoi qu'il arrive)
# 0 : Pas de coupe
job = esc + b"{IB;0001,0,0|}"

if __name__ == "__main__":
    print("Test 7: Hybride Feed (No Sensor)")
    send_job(job)
