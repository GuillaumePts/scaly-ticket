import socket
import time
from PIL import Image, ImageDraw, ImageFont
import sys
sys.path.append('.')
from src.zpl_engine import ZPLEngine
from src.models import TicketData

def main():
    printer_ip = "200.200.129.200"
    printer_port = 9100
    
    data = TicketData(
        Client="FERME",
        Commande="CMD123",
        DateLivraison="26/06/19",
        Libelle="6 Yaourt entier Abricot - 2X125G",
        CodeBarre10="26L222805",
        CodeBarre17="260712",
        CodeBarre01="13374270830099",
        Numlot="26L222805",
        Quantite=6
    )
    
    engine = ZPLEngine(203)
    # Generate full 3-up image (800x1200)
    image = engine._render_toshiba_band([data, data, data])
    
    img_w, img_h = image.size
    w_bytes = img_w // 8
    
    raw = image.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)
    
    # Compress the ENTIRE 1200 lines at once!
    comp = engine.compress_topix(w_bytes, img_h, inv)
    
    header = (
        b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
    )
    
    # THE HOLY GRAIL TRICK:
    # We send H=0300 (to bypass the firmware's strict parser limit that causes red light),
    # BUT we give it the payload for ALL 1200 lines!
    # NiceLabel does exactly this: its SG 5 has H=0300 but contains 528 lines of data!
    sg = f"{{SG;0000,0000,{img_w:04d},0300,3,".encode('ascii')
    clen = len(comp)
    sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
    
    footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    
    job_data = header + sg + footer
    
    print(f"Taille de l'image : {img_w}x{img_h}")
    print(f"Taille compressée totale : {len(comp)} octets")
    print("Envoi en UNE SEULE commande {SG} (Holy Grail trick)...")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    try:
        s.connect((printer_ip, printer_port))
        s.sendall(job_data)
        s.shutdown(socket.SHUT_WR)
        time.sleep(2.0)
        s.close()
        print("Envoyé avec succès !")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()
