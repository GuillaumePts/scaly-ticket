import socket
import os

IP_TOSHIBA = "200.200.129.82"
PORT = 9100
FILE_PATH = "impression_file.prn"

def send_raw_file():
    if not os.path.exists(FILE_PATH):
        print(f"Erreur : Le fichier {FILE_PATH} est introuvable.")
        return

    print(f"Lecture du fichier {FILE_PATH}...")
    with open(FILE_PATH, "rb") as f:
        data = f.read()
    
    print(f"Taille du fichier : {len(data)} octets.")
    
    print(f"Connexion à {IP_TOSHIBA}:{PORT}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10.0)
            s.connect((IP_TOSHIBA, PORT))
            print("Envoi en cours...")
            s.sendall(data)
            print("Flux envoyé à 100%.")
    except Exception as e:
        print(f"Erreur lors de l'envoi : {e}")

if __name__ == "__main__":
    send_raw_file()
