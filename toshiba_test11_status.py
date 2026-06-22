import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def test_status():
    esc = b"\x1b"
    # WS: Status Request
    job = esc + b"WS"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(job)
            print("Commande Status envoyée. Attente réponse...")
            try:
                response = s.recv(1024)
                print(f"Réponse brute : {response}")
            except socket.timeout:
                print("Pas de réponse (Timeout).")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    test_status()
