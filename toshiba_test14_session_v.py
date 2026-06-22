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
stx = b"\x02"
etx = b"\x03"

# Test 14: Session STX/ETX + Commande 'v' (Issue alternatif)
# Certains firmwares réseau n'aiment pas XS et préfèrent 'v'
job = (
    stx + 
    esc + b"{D0300,0800,0300|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    esc + b"{PC001;0100,0100,1,1,k,00,B=TEST 14 SESSION|}" +
    esc + b"{v;0001|}" +
    etx
)

if __name__ == "__main__":
    print("Test 14: Industrial Session + Command 'v'")
    send_job(job)
