import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter

def compress_topix(width_bytes: int, height_dots: int, raw_data: bytes) -> bytes:
    """Compression (Mode 3) identique au driver Seagull."""
    last_line = bytearray(width_bytes)
    comp_buffer = bytearray()

    for y in range(height_dots):
        line_start = y * width_bytes
        line_data = raw_data[line_start: line_start + width_bytes]

        line_arr = [[[0 for _ in range(9)] for _ in range(9)] for _ in range(8)]
        cl1 = 0
        i = 0
        for l1 in range(8):
            if i >= width_bytes:
                break
            cl2 = 0
            for l2 in range(1, 9):
                if i >= width_bytes:
                    break
                cl3 = 0
                for l3 in range(1, 9):
                    if i >= width_bytes:
                        break
                    val_xor = line_data[i] ^ last_line[i]
                    line_arr[l1][l2][l3] = val_xor
                    if val_xor > 0:
                        cl3 |= (1 << (8 - l3))
                    i += 1
                line_arr[l1][l2][0] = cl3
                if cl3 != 0:
                    cl2 |= (1 << (8 - l2))
            line_arr[l1][0][0] = cl2
            if cl2 != 0:
                cl1 |= (1 << (7 - l1))

        comp_buffer.append(cl1)
        if cl1 > 0:
            for l1 in range(8):
                for l2 in range(9):
                    for l3 in range(9):
                        val = line_arr[l1][l2][l3]
                        if val != 0:
                            comp_buffer.append(val)

        last_line = bytearray(line_data)

    # Tronquer les zéros de fin
    while len(comp_buffer) > 0 and comp_buffer[-1] == 0:
        comp_buffer.pop()

    return bytes(comp_buffer)

def draw_single_label(data: dict) -> Image.Image:
    """
    Dessine une étiquette individuelle de 30mm x 74.2mm.
    On dessine en paysage (594x240 dots) puis on pivote.
    """
    img_w, img_h = 594, 240
    img = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(img)
    
    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 36)
        font_normal = ImageFont.truetype("arial.ttf", 28)
        font_small  = ImageFont.truetype("arial.ttf", 22)
    except IOError:
        font_title  = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small  = ImageFont.load_default()

    # --- Libellé ---
    libelle = data["libelle"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), libelle, font=font_title)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(libelle, font=font_title)
    draw.text(((img_w - tw)//2, 10), libelle, fill=0, font=font_title)

    # --- Code-barres ---
    barcode_y = 65
    barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.25,
        'module_height': 15.0,
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    img.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
    barcode_bottom = barcode_y + bc_img.height

    # --- Textes GS1 ---
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
    
    # Rotation -> 240x594
    return img.transpose(Image.ROTATE_90)

def render_full_band(data_list):
    """
    Crée la bande complète : 101.6 mm x 74.2 mm (812 x 594 dots).
    Place 3 étiquettes côte à côte.
    """
    main = Image.new('1', (812, 594), color=1)
    
    # x_offset initial = 16 dots (2mm margin gauche)
    x_offset = 16
    for data in data_list[:3]:
        lbl = draw_single_label(data)
        main.paste(lbl, (x_offset, 0))
        # Largeur de l'étiquette (240) + Espace entre étiquettes (24 dots = 3mm)
        x_offset += 240 + 24
        
    return main

def build_job_sliced(image):
    """
    Génère le payload TPCL.
    Découpe l'image en blocs horizontaux (max 200 dots de haut) pour ne pas 
    saturer la mémoire tampon (RAM) de l'imprimante B-FV4D.
    """
    img_w, img_h = image.size
    
    # Header strict basé sur la conf d'usine (101.6 x 74.3 mm)
    header = (
        b"<xpml><page quantity='0' pitch='74.3 mm'></xpml>\r\n"
        b"{D0763,1016,0743|}\r\n"
        b"<xpml></page></xpml>\r\n"
        b"<xpml><page quantity='1' pitch='74.3 mm'></xpml>\r\n"
        b"{C|}\r\n"
    )
    
    sg_commands = b""
    CHUNK_H = 200 # Sécurité absolue pour la mémoire (NiceLabel utilise 300)
    
    for y in range(0, img_h, CHUNK_H):
        chunk_h = min(CHUNK_H, img_h - y)
        chunk = image.crop((0, y, img_w, y + chunk_h))
        
        raw = chunk.tobytes()
        inv = bytes(b ^ 0xFF for b in raw)
        comp = compress_topix(img_w // 8, chunk_h, inv)
        
        # Envoi du chunk à sa position Y
        sg = f"{{SG;0000,{y:04d},{img_w:04d},{chunk_h:04d},3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        sg_commands += sg
        
    footer = b"{XS;I,0001,0002C4000|}\r\n<xpml></page></xpml>\r\n"
    return header + sg_commands + footer

if __name__ == '__main__':
    # Exemple de données
    dummy_data = {
        "libelle": "MIMO 24 MOIS",
        "gtin": "03760205241031",
        "date_expiration": "260618",
        "lot": "2103",
        "num_lot_display": "DLC 18/06/2026 LOT 2103"
    }
    
    # Générer 3 étiquettes
    img = render_full_band([dummy_data, dummy_data, dummy_data])
    img.save("toshiba_final_preview.png")
    
    job = build_job_sliced(img)
    
    if '--print' in sys.argv:
        print("Envoi à l'imprimante (Mode Sliced 3-up)...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect(('200.200.129.200', 9100))
            s.sendall(job)
            s.shutdown(socket.SHUT_WR)
            print("Envoyé avec succès !")
        except Exception as e:
            print(f"Erreur réseau : {e}")
    else:
        print("Mode aperçu. Ouvrez toshiba_final_preview.png pour vérifier l'image.")
        print("Lancez avec '--print' pour imprimer physiquement.")
