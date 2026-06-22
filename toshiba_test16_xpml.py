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
            print("Flux XPML envoyé. Observez l'imprimante.")
    except Exception as e:
        print(f"Erreur : {e}")

esc = b"\x1b"

# Construction du job basé sur la capture utilisateur
# Note: On garde ESC devant les accolades car c'est la norme TPCL, 
# même si le texte capturé ne le montre pas forcément (car invisible).

job_xpml = (
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    esc + b"{D0763,1016,0743|}" +
    esc + b"{C|}" +
    esc + b"{L|}" +
    # Un texte simple pour vérifier
    esc + b"{PC001;0100,0100,1,1,k,00,B=TEST XPML OK|}" +
    # On tente le XS avec les paramètres du driver s'ils existent, 
    # sinon on utilise une version standard mais encapsulée.
    esc + b"{XS;0001,0004,0000,1,1,0,0,0|}" +
    b"<xpml></page></xpml>"
)

if __name__ == "__main__":
    print("Test 16: XPML Encapsulation (Driver Emulation)")
    send_job(job_xpml, "XPML + HYBRID TPCL")
