import socket

host = "200.200.129.82"
port = 9100

def test_tpcl_minimal():
    # ESC AX (Reset)
    # ESC C (Clear buffer)
    # ESC L (Label Start)
    # ESC PC001;0100,0100,1,1,k,00,B=HELLO| (Text)
    # ESC XS (Print)
    # ESC I (Feed)
    
    esc = b"\x1b"
    job = esc + b"AX" + esc + b"C" + esc + b"L" + \
          esc + b"PC001;0100,0100,1,1,k,00,B=HELLO|" + \
          esc + b"XS" + esc + b"I"
    
    print(f"Envoi du flux TPCL minimal à {host}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((host, port))
            s.sendall(job)
            print("Flux envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    test_tpcl_minimal()
