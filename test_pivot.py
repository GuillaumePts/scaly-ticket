import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from test_toshiba_layout_fix import compress_topix, DATA

# LA CONFIGURATION QUI A MARCHÉ (pivot.jpg)
CANVAS_W = 616
CANVAS_H = 300

def render_label(data):
    main = Image.new('1', (CANVAS_W, CANVAS_H), color=1)
    
    # Sous-image (300 de large, 240 de haut)
    sub = Image.new('1', (300, 240), color=1)
    draw = ImageDraw.Draw(sub)
    try: font = ImageFont.truetype("arialbd.ttf", 20)
    except: font = ImageFont.load_default()
    
    draw.text((10, 10), data["libelle"], fill=0, font=font)
    
    # Code-barres
    barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.20,
        'module_height': 8.0,  
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    sub.paste(bc_img, (10, 40))
    
    # Rotation (240x300 portrait)
    sub_rot = sub.transpose(Image.ROTATE_90)
    
    # On la colle à 16 pixels (2mm) pour esquiver le trou !
    main.paste(sub_rot, (16, 0))
    return main

def build_job(image):
    raw = image.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)
    img_w, img_h = image.size
    comp = compress_topix(img_w // 8, img_h, inv)
    
    # Le Header qui a fait ses preuves (74.3mm)
    header = (
        b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>\r\n"
        b"{D0763,1016,0743|}\r\n"
        b"<xpml></page></xpml>\r\n"
        b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>\r\n"
        b"{C|}\r\n"
    )
    
    sg = f"{{SG;0000,0000,{img_w:04d},{img_h:04d},3,".encode('ascii')
    clen = len(comp)
    sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
    
    footer = b"{XS;I,0001,0002C4000|}\r\n<xpml></page></xpml>\r\n"
    return header + sg + footer

if __name__ == '__main__':
    img = render_label(DATA)
    job = build_job(img)
    img.save("test_pivot_preview.png")
    
    if '--print' in sys.argv:
        print("Envoi de test_pivot.py...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(('200.200.129.200', 9100))
        s.sendall(job)
        s.shutdown(socket.SHUT_WR)
        print("Envoye !")
