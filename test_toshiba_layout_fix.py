"""
Test de layout Toshiba B-FV4D - Validation visuelle LOCALE
Génère une image PNG pour prévisualiser le rendu AVANT envoi à l'imprimante.

Dimensions référence depuis driver officiel :
  - {D0763,1016,0743|} : 76.3mm de large (printhead), feed 101.6mm, pitch 74.3mm
  - {SG;0126,0126,0616,0300,3,...} : bitmap 616 bytes x 300 dots, offset x=126, y=126

Plan :
  - 1 étiquette physique = 76.3mm x 74.3mm (direction avancement)
  - Bitmap = 616 dots de large (76.3mm x 8 dots/mm ≈ 610 → 616 arrondi à multiple de 8)
  - Hauteur = 300 dots (74.3mm x ~4 dots/mm ? → en réalité le driver utilise 300 dots)
  - L'imprimante gère elle-même la répétition 3-up physique

Usage : python test_toshiba_layout_fix.py
"""
import io
import sys
import socket
import time
from PIL import Image, ImageDraw, ImageFont

try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False
    print("[WARN] python-barcode non installé. Le code-barres ne sera pas généré.")

# ============================================================
# CONFIGURATION
# ============================================================
IP_TOSHIBA = "200.200.129.200"
PORT = 9100

# Dimensions exactes issues du driver officiel
# Dimensions exactes issues de l'étiquette 30x115mm
# Dimensions exactes issues de l'étiquette 30x115mm
# Le canevas interne est dessiné en mode PAYSAGE
# Puis il sera pivoté pour devenir PORTRAIT (304x616) et envoyé à l'imprimante.
# Dimensions EXACTES de la demande : 30mm de large x 115mm de haut
# 30 mm = 240 dots
# 115 mm = 920 dots
CANVAS_W = 240   
CANVAS_H = 590   

# Offset pour éviter le trou de 2mm à gauche (2mm = 16 dots)
OFFSET_X = 16   
OFFSET_Y = 0   

PITCH_MM = 74.3 # Pitch de 74.3 mm pour le test scientifique
DPI = 203
DOTS_PER_MM = 8.0


# ============================================================
# DONNÉES DE TEST (reproduire une ligne du CSV)
# ============================================================
DATA = {
    "libelle":         "6 Yaourt Brasse Coco 140G RGF - 140G",
    "gtin":            "13374270830099",
    "date_expiration": "260712",   # Format YYMMDD
    "lot":             "26L222805",
    "num_lot_display": "LOT 26L222805 12/07/26  Conservation 4/6 \u00b0C",
}


# ============================================================
# ALGORITHME DE COMPRESSION TOPIX (Mode 3 - validé octet par octet)
# ============================================================
def compress_topix(width_bytes: int, height_dots: int, raw_data: bytes) -> bytes:
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

    # Tronquer les zéros de fin (comportement driver officiel)
    while len(comp_buffer) > 0 and comp_buffer[-1] == 0:
        comp_buffer.pop()

    return bytes(comp_buffer)


# ============================================================
# RENDU PILLOW - Génère le bitmap de l'étiquette
# ============================================================
def render_label(data: dict) -> Image.Image:
    """
    Crée une étiquette pure 30x74mm (Test scientifique).
    On dessine à l'horizontale (590x240) puis on pivote.
    """
    # Canevas horizontal de 590x240
    img_w, img_h = 590, 240
    image = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(image)

    # --- Polices ---
    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 30)
        font_normal = ImageFont.truetype("arial.ttf", 24)
        font_small  = ImageFont.truetype("arial.ttf", 20)
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

    # --- Code-barres ---
    barcode_y = 50
    if HAS_BARCODE:
        barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
        stream = io.BytesIO()
        fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
        fp.write(stream, options={
            'dpi': 203,
            'module_width': 0.35,
            'module_height': 8.0,  
            'quiet_zone': 2.0,
            'write_text': False,
        })
        stream.seek(0)
        bc_img = Image.open(stream).convert('1')
        image.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
        barcode_bottom = barcode_y + bc_img.height
    else:
        draw.rectangle([(img_w - 400)//2, barcode_y, (img_w + 400)//2, barcode_y + 60], outline=0)
        barcode_bottom = barcode_y + 60

    # --- Texte GS1 ---
    gs1_text = f"(01){data['gtin']}(17){data['date_expiration']}(10){data['lot']}"
    try:
        bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(gs1_text, font=font_small)
    draw.text(((img_w - tw)//2, barcode_bottom + 8), gs1_text, fill=0, font=font_small)

    # --- Ligne LOT/Date ---
    lot_text = data["num_lot_display"].encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(lot_text, font=font_normal)
    draw.text(((img_w - tw)//2, barcode_bottom + 35), lot_text, fill=0, font=font_normal)

    # Rotation pour passer en mode PORTRAIT (240x590)
    image = image.transpose(Image.ROTATE_90)

    return image


# ============================================================
# ASSEMBLAGE DU JOB TPCL
# ============================================================
def build_tpcl_job(image: Image.Image) -> bytes:
    # Inversion des bits
    raw = image.tobytes()
    inverted = bytes(b ^ 0xFF for b in raw)

    img_w, img_h = image.size
    w_bytes = img_w // 8

    # Compression TOPIX Mode 3
    compressed = compress_topix(w_bytes, img_h, inverted)
    clen = len(compressed)
    belen = bytes([clen >> 8, clen & 0xFF])

    crlf = b"\r\n"

    header = (
        f"<xpml><page quantity='0' pitch='{PITCH_MM} mm'></xpml>".encode('ascii') +
        b"{D0763,1016,0743|}" + crlf +
        b"<xpml></page></xpml>" +
        f"<xpml><page quantity='1' pitch='{PITCH_MM} mm'></xpml>".encode('ascii') +
        b"{C|}" + crlf
    )

    # Commande SG : dimensions réelles de l'image finale
    sg_cmd = (
        f"{{SG;{OFFSET_X:04d},{OFFSET_Y:04d},{img_w:04d},{img_h:04d},3,".encode('ascii')
        + belen + compressed + b"|}" + crlf
    )

    footer = (
        b"{XS;I,0001,0000C5000|}" + crlf +
        b"<xpml></page></xpml><xpml><end/></xpml>"
    )

    return header + sg_cmd + footer


# ============================================================
# ENVOI À L'IMPRIMANTE
# ============================================================
def send_to_printer(job: bytes):
    print(f"Envoi de {len(job)} bytes à {IP_TOSHIBA}:{PORT} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10.0)
        s.connect((IP_TOSHIBA, PORT))
        s.sendall(job)
        s.shutdown(socket.SHUT_WR)
        print("Données envoyées. Attente de 2s avant fermeture socket...")
        time.sleep(2.0)
    print("Socket fermée. Job terminé.")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=== Toshiba B-FV4D - Test Layout Fix (30x115mm) ===")
    print(f"Canvas (Avant rotation) : {CANVAS_W} x {CANVAS_H} dots")
    print(f"Pitch  : {PITCH_MM} mm")

    # 1. Rendu
    img = render_label(DATA)

    # 2. Sauvegarde PNG pour prévisualisation
    preview_path = "test_layout_preview.png"
    img.save(preview_path)
    print(f"\n[OK] Prévisualisation sauvegardée : {preview_path}")
    print("     Ouvre ce fichier pour vérifier le rendu AVANT d'imprimer.")

    # 3. Assemblage job TPCL
    job = build_tpcl_job(img)
    print(f"[OK] Job TPCL assemblé : {len(job)} bytes")

    # 4. Envoi conditionnel
    if "--print" in sys.argv:
        send_to_printer(job)
    else:
        print("\n[INFO] Pour envoyer à l'imprimante, relancer avec : python test_toshiba_layout_fix.py --print")
