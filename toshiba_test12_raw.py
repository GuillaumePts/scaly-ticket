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

# Test 12: Raw Text
# Si le pilote "Generic Text Only" fonctionne, peut-être qu'elle attend juste du texte brut
job = b"TEST RAW TEXT\r\n"

if __name__ == "__main__":
    print("Test 12: Raw Text")
    send_job(job)
