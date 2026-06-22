import socket

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def send_job(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(data)
            print("Flux 'Graphic Raw' envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

# Génération d'un bloc noir de 100x100 pixels
# 100 pixels / 8 = 13 bytes par ligne (arrondi)
width_dots = 104 # Multiple de 8
width_bytes = width_dots // 8
height_dots = 100
# Un bloc noir = tous les bits à 1 (\xff)
black_line = b"\xff" * width_bytes
graphic_data = black_line * height_dots

# Commande SG : {SG;xxxx,yyyy,wwww,hhhh,m,data|}
# m=0 : Mode Raw (non compressé)
sg_command = f"{{SG;0100,0100,{width_bytes:04d},{height_dots:04d},0,".encode('ascii') + graphic_data + b"|}"

crlf = b"\r\n"
job = (
    b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>{D0763,1016,0743|}\r\n<xpml></page></xpml>" +
    b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>{C|}\r\n" +
    sg_command + crlf +
    b"{XS;I,0001,0000C5000|}\r\n" +
    b"<xpml></page></xpml><xpml><end/></xpml>"
)

if __name__ == "__main__":
    print(f"Envoi d'un bloc noir de {width_dots}x{height_dots} pixels...")
    send_job(job)
