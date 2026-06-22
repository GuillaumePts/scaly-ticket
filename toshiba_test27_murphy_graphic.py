import socket
from PIL import Image, ImageDraw, ImageFont
import io

IP_TOSHIBA = "200.200.129.82"
PORT = 9100

def generate_murphy_graphic():
    # Dimensions de l'étiquette (32mm @ 203 DPI = ~256 dots)
    width, height = 600, 250 # Largeur généreuse pour le test
    
    # Création de l'image (1-bit monochrome)
    image = Image.new('1', (width, height), color=1) # 1 = Blanc
    draw = ImageDraw.Draw(image)
    
    # Texte
    try:
        # On essaie d'utiliser une police système, sinon celle par défaut
        font = ImageFont.load_default()
    except:
        font = None

    text = "LOI DE MURPHY :\nTout ce qui peut mal tourner\ntournera mal."
    draw.text((20, 20), text, fill=0, font=font) # 0 = Noir
    
    # Inversion des bits pour TPCL (1=Noir, 0=Blanc dans certains modes, 
    # mais en mode '1' de Pillow 0=Noir, ce qui est standard)
    
    # Conversion en bytes (Raw Bitmap)
    # Chaque ligne doit être complétée pour faire un multiple de 8 bits
    img_bytes = image.tobytes()
    return width, height, img_bytes

def send_job():
    width_dots, height_dots, data = generate_murphy_graphic()
    width_bytes = width_dots // 8
    
    # Commande SG : {SG;xxxx,yyyy,wwww,hhhh,0,data|}
    # On utilise le mode 0 (Raw)
    sg_command = f"{{SG;0020,0020,{width_bytes:04d},{height_dots:04d},0,".encode('ascii') + data + b"|}"
    
    crlf = b"\r\n"
    job = (
        b"<xpml><page quantity='0' pitch='32.0 mm'></xpml>{D1000,1000,0320|}\r\n<xpml></page></xpml>" +
        b"<xpml><page quantity='1' pitch='32.0 mm'></xpml>{C|}\r\n" +
        sg_command + crlf +
        b"{XS;I,0001,0000C5000|}\r\n" +
        b"<xpml></page></xpml><xpml><end/></xpml>"
    )

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((IP_TOSHIBA, PORT))
            s.sendall(job)
            print("Flux graphique envoyé.")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    send_job()
