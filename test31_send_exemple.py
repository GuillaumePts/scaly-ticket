import socket
import sys

def send_file(filename):
    with open(filename, 'rb') as f:
        job = f.read()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect(('200.200.129.200', 9100))
        s.sendall(job)
        s.shutdown(socket.SHUT_WR)
        import time
        time.sleep(2.0)
        s.close()
        print(f"[{filename}] Envoyé avec succès !")
    except Exception as e:
        print(f"Erreur d'envoi: {e}")

if __name__ == '__main__':
    send_file('prn_file_exemple/exemplePrn.prn')
