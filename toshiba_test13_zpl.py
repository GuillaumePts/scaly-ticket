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

# Test 13: ZPL propre
# Juste pour être sûr à 100% que ce n'est pas du ZPL
job = b"^XA^FO50,50^A0N,50,50^FDTEST ZPL^FS^XZ"

if __name__ == "__main__":
    print("Test 13: Clean ZPL")
    send_job(job)
