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

# Test 10: Commande de ligne graphique simple (RV)
# Si les polices posent problème, une ligne graphique devrait passer.
# {RV; x1, y1, x2, y2, type |}
job = (
    esc + b"{D0300,0800,0300|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    esc + b"{RV;0050,0050,0500,0060,0|}" +
    esc + b"{XS;0001,0004,0000,0,0,0,0,0|}"
)

if __name__ == "__main__":
    print("Test 10: Hybride + Graphic Line (RV)")
    send_job(job)
