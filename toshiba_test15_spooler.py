import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Spooler-Style' envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

esc = b"\x1b"
# Test 15: Simulation Spooler Windows Text-Only
# Utilise les commandes standard mais avec des terminaisons \r\n strictes après chaque bloc
# Et termine par \x0c (Form Feed) ou \x04 (EOT)
job = (
    esc + b"AX" + b"\r\n" +                    # Reset
    esc + b"D0300,0800,0300" + b"\r\n" +       # Dimensions
    esc + b"C" + b"\r\n" +                    # Clear
    esc + b"L" + b"\r\n" +                    # Label Start
    esc + b"PC001;0100,0100,1,1,k,00,B=TEST DRIVER SIM|" + b"\r\n" +
    esc + b"XS;0001,0004,0000,1,0,0,0,0" + b"\r\n" +
    b"\x0c" + b"\x04"                          # Form Feed + EOT (Standard Windows)
)

if __name__ == "__main__":
    print("Test 15: Windows Spooler Emulation")
    send_job(job)
