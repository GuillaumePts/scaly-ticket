import socket
from PIL import Image, ImageDraw, ImageFont

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def create_murphy_image():
    # Largeur du driver : 616 dots (77 bytes)
    # Hauteur du driver : 300 dots
    width_dots = 616
    height_dots = 300
    
    # Image 1-bit (monochrome)
    image = Image.new('1', (width_dots, height_dots), color=1) # 1=Blanc
    draw = ImageDraw.Draw(image)
    
    text = "LOI DE MURPHY\n\nTout ce qui peut\nmal tourner\ntournera mal."
    # On dessine le texte en noir (0)
    draw.text((10, 10), text, fill=0)
    
    return width_dots, height_dots, image.tobytes()

def send_job():
    w_dots, h_dots, raw_data = create_murphy_image()
    w_bytes = w_dots // 8
    
    crlf = b"\r\n"
    
    # On clone la structure EXACTE du driver
    header = (
        b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>" +
        b"{D0763,1016,0743|}" + crlf +
        b"<xpml></page></xpml>" +
        b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>" +
        b"{C|}" + crlf
    )
    
    # Commande SG (m=0 pour Raw)
    # On utilise les coordonnées du driver (0126, 0126)
    sg_command = f"{{SG;0126,0126,{w_bytes:04d},{h_dots:04d},0,".encode('ascii') + raw_data + b"|}" + crlf
    
    # Sortie XS exacte du driver
    footer = (
        b"{XS;I,0001,0000C5000|}" + crlf +
        b"<xpml></page></xpml><xpml><end/></xpml>"
    )
    
    job = header + sg_command + footer

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(job)
            print("Flux Murphy Final (Graphique) envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    send_job()
