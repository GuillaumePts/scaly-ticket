import socket
import time

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data, desc):
    print(f"--- {desc} ---")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

crlf = b"\r\n"

# Test 19: FEED pur sans ESC dans une session XPML
job = (
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    b"{f0001|}" + crlf +
    b"<xpml></page></xpml>" +
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    print("Test 19: FEED SANS ESC (Mode XPML strict)")
    send_job(job, "FEED TEST NO ESC")
