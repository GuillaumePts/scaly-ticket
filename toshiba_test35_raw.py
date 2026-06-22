import socket
import time

def main():
    printer_ip = "200.200.129.200"
    printer_port = 9100
    file_path = "prn_file_exemple/exemplePrn.prn"
    
    print(f"Lecture du fichier binaire brut : {file_path}")
    try:
        with open(file_path, "rb") as f:
            job_data = f.read()
    except FileNotFoundError:
        print(f"Erreur : Le fichier {file_path} est introuvable.")
        return

    print(f"Taille du job : {len(job_data)} octets.")
    print(f"Envoi au port {printer_port} de {printer_ip}...")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect((printer_ip, printer_port))
        s.sendall(job_data)
        
        # Fermeture propre (très important pour les imprimantes réseau Toshiba)
        s.shutdown(socket.SHUT_WR)
        print("Données envoyées avec succès. Attente de la fin de l'impression...")
        time.sleep(2.0)
        s.close()
        print("Connexion fermée. Le job est terminé !")
        
    except Exception as e:
        print(f"Erreur de communication : {e}")
        
if __name__ == "__main__":
    main()
