import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from test_toshiba_layout_fix import compress_topix, DATA

def draw_single_label(data: dict) -> Image.Image:
    img_w, img_h = 920, 240
    img = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(img)
    
    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 36)
        font_normal = ImageFont.truetype("arial.ttf", 28)
        font_small  = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font_title  = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small  = ImageFont.load_default()

    libelle = data["libelle"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), libelle, font=font_title)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(libelle, font=font_title)
    draw.text(((img_w - tw)//2, 10), libelle, fill=0, font=font_title)

    barcode_y = 60
    barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.40,
        'module_height': 20.0,
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    img.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
    barcode_bottom = barcode_y + bc_img.height

    gs1_text = f"(01){data['gtin']}(17){data['date_expiration']}(10){data['lot']}"
    try:
        bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(gs1_text, font=font_small)
    draw.text(((img_w - tw)//2, barcode_bottom + 10), gs1_text, fill=0, font=font_small)

    lot_text = data["num_lot_display"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(lot_text, font=font_normal)
    draw.text(((img_w - tw)//2, barcode_bottom + 45), lot_text, fill=0, font=font_normal)
    
    return img.transpose(Image.ROTATE_90)

def render_full_band(data_list):
    # Bande exacte selon l'usine : 97.5mm (780 dots) x 120.1mm (960 dots). 
    # Prenons 780 x 1200.
    main = Image.new('1', (780, 1200), color=1)
    
    x_offset = 24
    for data in data_list[:3]:
        lbl = draw_single_label(data)
        main.paste(lbl, (x_offset, 0))
        x_offset += 240 + 24
        
    return main

def build_job_no_empty(image):
    img_w, img_h = image.size
    
    # Exact XPML headers sans saut de ligne en trop
    header = (
        b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
    )
    
    sg_commands = b""
    CHUNK_H = 300
    
    for y in range(0, img_h, CHUNK_H):
        chunk_h = min(CHUNK_H, img_h - y)
        chunk = image.crop((0, y, img_w, y + chunk_h))
        
        raw = chunk.tobytes()
        inv = bytes(b ^ 0xFF for b in raw)
        comp = compress_topix(img_w // 8, chunk_h, inv)
        
        # SI LE CHUNK EST VIDE (Payload=0), ON NE L'ENVOIE PAS !
        if len(comp) == 0:
            continue
            
        sg = f"{{SG;0024,{y:04d},{img_w:04d},{chunk_h:04d},3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        sg_commands += sg
        
    footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    return header + sg_commands + footer

if __name__ == '__main__':
    # Generer 3 etiquettes
    img = render_full_band([DATA, DATA, DATA])
    job = build_job_no_empty(img)
    if '--print' in sys.argv:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect(('200.200.129.200', 9100))
            s.sendall(job)
            s.shutdown(socket.SHUT_WR)
            import time
            time.sleep(2.0)
            s.close()
            print("Envoyé sans chunks vides")
        except Exception as e:
            print(f"Erreur: {e}")
    else:
        print("Pret. Taille du job:", len(job))
