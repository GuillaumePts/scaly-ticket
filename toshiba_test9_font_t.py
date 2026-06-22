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

# Test 9: Utilisation des Polices Bitmapped (T) au lieu de Outline (PC)
# La commande T est la plus ancienne et la plus compatible.
# {T; x, y, font, w_mul, h_mul, align, data |}
# font 21 = Font standard 2, w_mul=1, h_mul=1
job = (
    esc + b"{D0300,0800,0300|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    esc + b"{T;0100,0100,21,1,1,0,TEST FONT T|}" +
    esc + b"{XS;0001,0004,0000,0,0,0,0,0|}"
)

if __name__ == "__main__":
    print("Test 9: Hybride + Bitmapped Font (T)")
    send_job(job)
