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

# Test 5: Hybride avec délimiteurs de fin explicites
# Certains firmwares exigent que le flux se termine par une nouvelle ligne ou un caractère nul
# Et on ajoute un texte plus long pour être sûr que ça ne soit pas un problème de zone
job = (
    esc + b"{D0300,0800,0300|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    esc + b"{PC001;0100,0100,1,1,k,00,B=TEST 5 PRINT OK?|}" +
    esc + b"{XS;0001,0004,0000,1,0,0,0,0|}" +
    b"\r\n"
)

if __name__ == "__main__":
    print("Test 5: Hybride + Line Terminators")
    send_job(job)
