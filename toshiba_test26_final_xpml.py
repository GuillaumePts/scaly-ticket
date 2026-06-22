import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Sentinel' envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

crlf = b"\r\n"

# LA STRUCTURE EXACTE DU DRIVER (AU BIT PRÈS)
job = (
    # 1. Sentinelle de config (s'ouvre et se ferme de suite)
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
    # 2. Commande TPCL brute
    b"{D0763,1016,0743|}" + crlf +
    # 3. Sentinelle de fin de config
    b"<xpml></page></xpml>" +
    
    # 4. Sentinelle de début de job
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
    # 5. Commandes TPCL brutes
    b"{C|}" + crlf +
    b"{PC001;0100,0100,1,1,k,00,B=ENFIN CA MARCHE ?|}" + crlf +
    b"{PC002;0100,0200,1,1,k,00,B=TEST STRUCTURE SENTINELLE|}" + crlf +
    b"{XS;I,0001,0000C5000|}" + crlf +
    
    # 6. Sentinelle de fin de job
    b"<xpml></page></xpml>" +
    # 7. Sentinelle de fin de session
    b"<xpml><end/></xpml>"
)

if __name__ == "__main__":
    send_job(job)
