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
# Test 4: Minimaliste absolu (Reset + Feed)
# Juste pour voir si elle bouge mécaniquement
job = esc + b"AX" + esc + b"I" + b"\n"

if __name__ == "__main__":
    print("Test 4: Reset + Feed (Mécanique uniquement)")
    send_job(job)
