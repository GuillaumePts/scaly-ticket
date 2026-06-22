import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from test_toshiba_layout_fix import compress_topix, DATA

CANVAS_W = 240
CANVAS_H = 920

def render_label(data):
    img_w, img_h = 920, 240
    image = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(image)
    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 36)
        font_normal = ImageFont.truetype("arial.ttf", 28)
        font_small  = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_title  = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small  = ImageFont.load_default()

    # --- Libellé produit ---
    libelle = data["libelle"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), libelle, font=font_title)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(libelle, font=font_title)
    draw.text(((img_w - tw)//2, 10), libelle, fill=0, font=font_title)

    # --- Code-barres géant ---
    barcode_y = 60
    barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.40,     # Très large pour remplir les 115mm !
        'module_height': 20.0,    # Hauteur (qui deviendra la largeur sur 30mm)
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    image.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
    barcode_bottom = barcode_y + bc_img.height

    # --- Texte GS1 ---
    gs1_text = f"(01){data['gtin']}(17){data['date_expiration']}(10){data['lot']}"
    try:
        bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(gs1_text, font=font_small)
    draw.text(((img_w - tw)//2, barcode_bottom + 10), gs1_text, fill=0, font=font_small)

    # --- Ligne LOT/Date ---
    lot_text = data["num_lot_display"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(lot_text, font=font_normal)
    draw.text(((img_w - tw)//2, barcode_bottom + 45), lot_text, fill=0, font=font_normal)
    
    # Rotation (240x920)
    image = image.transpose(Image.ROTATE_90)
    return image

def build_job(image):
    raw = image.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)
    img_w, img_h = image.size
    comp = compress_topix(img_w // 8, img_h, inv)
    
    # PITCH = 0000 pour forcer le mode Continu pur ! (Désactive le capteur)
    header = (
        b"<xpml><page quantity='0' pitch='0.0 mm'></xpml>\r\n"
        b"{D0000,1016,1150|}\r\n"
        b"<xpml></page></xpml>\r\n"
        b"<xpml><page quantity='1' pitch='0.0 mm'></xpml>\r\n"
        b"{C|}\r\n"
    )
    
    sg = f"{{SG;0016,0000,{img_w:04d},{img_h:04d},3,".encode('ascii')
    clen = len(comp)
    sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
    
    footer = b"{XS;I,0001,0002C4000|}\r\n<xpml></page></xpml>\r\n"
    return header + sg + footer

if __name__ == '__main__':
    img = render_label(DATA)
    job = build_job(img)
    if '--print' in sys.argv:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(('200.200.129.200', 9100))
        s.sendall(job)
        s.shutdown(socket.SHUT_WR)
        print("Envoye V6 (Pitch 0000 Continu)")
