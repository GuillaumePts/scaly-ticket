import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from src.models import TicketData

class ZPLEngine:
    def __init__(self, dpi: int):
        self.dpi = dpi
        # 203 DPI -> 8 dots/mm
        # 300 DPI -> 11.81 dots/mm
        if self.dpi == 300:
            self.dots_per_mm = 11.81
        else:
            self.dots_per_mm = 8.0
        
        # Offsets X calculés pour le 3-up (standard)
        self.pitch_dots = int(32 * self.dots_per_mm)

    def mm_to_dots(self, mm: float) -> int:
        return int(mm * self.dots_per_mm)

    def generate_separator_zpl(self, next_product_name: str) -> str:
        """Génère une étiquette de séparation visuelle pour l'opérateur."""
        width_dots = self.mm_to_dots(115)
        height_dots = self.mm_to_dots(30)
        
        y_text = self.mm_to_dots(10)
        font_h = self.mm_to_dots(4)
        
        text_to_draw = f">>> {next_product_name} <<<"
        
        zpl_parts = [
            "^XA",
            f"^PW{width_dots}",
            f"^LL{height_dots}",
            "^CI28",
            # Horizontal lines
            f"^FO0,0^GB{width_dots},{self.mm_to_dots(3)},3^FS",
            f"^FO0,{y_text}^A0N,{font_h},{font_h}^FB{width_dots},1,0,C^FD{text_to_draw}^FS",
            f"^FO0,{height_dots - self.mm_to_dots(3)}^GB{width_dots},{self.mm_to_dots(3)},3^FS",
            "^XZ"
        ]
        return "\n".join(zpl_parts)

    def compress_topix(self, width_bytes: int, height_dots: int, raw_data: bytes) -> bytes:
        """Compresse les données graphiques bitmap brutes en mode TOPIX (XOR RLE)."""
        last_line = bytearray(width_bytes)
        comp_buffer = bytearray()
        
        for y in range(height_dots):
            line_start = y * width_bytes
            line_data = raw_data[line_start : line_start + width_bytes]
            
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
                for l1_idx in range(8):
                    for l2_idx in range(9):
                        for l3_idx in range(9):
                            val = line_arr[l1_idx][l2_idx][l3_idx]
                            if val != 0:
                                comp_buffer.append(val)
            
            last_line = bytearray(line_data)
            
        # Tronquer les zéros de fin (comportement driver officiel / test 34)
        while len(comp_buffer) > 0 and comp_buffer[-1] == 0:
            comp_buffer.pop()

        return bytes(comp_buffer)

    # -----------------------------------------------------------------------
    # Constantes Toshiba B-FV4D (issues des tests de juin 2026)
    # {D1221,0975,1201|} : Matrice 3-up sur 97.5mm de large, pitch 122.1mm
    # Canvas multiple de 8 : 800x1200 dots
    # -----------------------------------------------------------------------
    TOSHIBA_CANVAS_W = 768
    TOSHIBA_CANVAS_H = 1200
    TOSHIBA_CHUNK_H  = 300

    def _draw_toshiba_single_label(self, data: TicketData, styling: dict = None) -> Image.Image:
        """Dessine une étiquette individuelle (115x30mm) en paysage puis la pivote."""
        styling = styling or {}
        img_w, img_h = 920, 224
        img = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(img)
        
        try:
            t_font = "arialbd.ttf" if styling.get("title_bold") else "arial.ttf"
            g_font = "arialbd.ttf" if styling.get("gs1_bold") else "arial.ttf"
            l_font = "arialbd.ttf" if styling.get("lot_bold") else "arial.ttf"
            
            font_title  = ImageFont.truetype(t_font, max(10, 28 + styling.get("title_size", 0)))
            font_small  = ImageFont.truetype(g_font, max(10, 20 + styling.get("gs1_size", 0)))
            font_normal = ImageFont.truetype(l_font, max(10, 20 + styling.get("lot_size", 0)))
        except IOError:
            font_title  = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small  = ImageFont.load_default()

        # Libellé
        libelle = data.libelle.encode('latin-1', 'ignore').decode('latin-1')
        try:
            bbox = draw.textbbox((0, 0), libelle, font=font_title)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(libelle, font=font_title)
        draw.text(((img_w - tw)//2, 25), libelle, fill=0, font=font_title)

        # Code-barres
        barcode_y = 55
        barcode_data = f"01{data.gtin}17{data.date_expiration}10{data.lot}"
        stream = io.BytesIO()
        # On force 0.375 pour avoir exactement 3 dots (203 dpi) -> netteté parfaite et bonne largeur
        fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
        fp.write(stream, options={
            'dpi': 203,
            'module_width': 0.375,
            'module_height': 11.0,
            'quiet_zone': 2.0,
            'write_text': False,
        })
        stream.seek(0)
        bc_img = Image.open(stream).convert('1')
        img.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
        barcode_bottom = barcode_y + bc_img.height

        # Texte sous code-barres
        gs1_text = f"(01){data.gtin}(17){data.date_expiration}(10){data.lot}"
        try:
            bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(gs1_text, font=font_small)
        draw.text(((img_w - tw)//2, barcode_bottom + 8), gs1_text, fill=0, font=font_small)

        # Lot et DLC
        lot_text = data.num_lot_display.encode('latin-1', 'ignore').decode('latin-1')
        try:
            bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(lot_text, font=font_normal)
        draw.text(((img_w - tw)//2, barcode_bottom + 42), lot_text, fill=0, font=font_normal)
        
        # On retourne l'étiquette orientée pour être collée dans la bande 3-up
        return img.transpose(Image.ROTATE_90)

    def _render_toshiba_band(self, data_list: list, offset_x: int = 0, offset_y: int = 0, styling: dict = None) -> Image.Image:
        """Génère la bande complète 3-up (Canvas 800x1200)."""
        # Assemblage sur le canvas global 3-up
        main = Image.new('1', (self.TOSHIBA_CANVAS_W, self.TOSHIBA_CANVAS_H), color=1)
        # Pitch de 33mm (264 points) entre chaque étiquette pour éviter le décalage progressif
        # On démarre à 12 pour éviter le bug firmware de la B-EV4 sur le pixel 0
        x_offsets = [12, 276, 540]
        for i, data in enumerate(data_list[:3]):
            lbl = self._draw_toshiba_single_label(data, styling)
            main.paste(lbl, (x_offsets[i] + offset_x, 0 + offset_y))
        return main

    def _build_tpcl_job(self, image: Image.Image, quantity: int = 1, xpml_pitch: bool = True, d_param: str = None) -> bytes:
        """Construit le flux TPCL binaire complet (header XPML + SG graphique + footer XS).

        xpml_pitch=True  -> B-FV4D : balises avec attribut pitch='120.1 mm'
        xpml_pitch=False -> B-EV4 Gravigny/FLIPOU : sans attribut pitch (firmware B-EV4 le rejette)
        d_param : chaine 'PITCH,WIDTH,HEIGHT' en 1/10mm pour la commande {D}.
                  Defaut : '1221,0975,1201' (rouleau 3-up standard).
                  4-up B-EV4 : configurer dans printers.json via 'd_param_4up'.
        """
        img_w, img_h = image.size
        w_bytes = img_w // 8
        d_bytes = (d_param or "1221,0975,1201").encode('ascii')
        crlf = b"\r\n"


        if xpml_pitch:
            # B-FV4D : balises XPML avec attribut pitch (comportement d'origine validé juin 2026)
            page_open = b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>"
            page_cont = b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>"
        else:
            # B-EV4 Gravigny/FLIPOU : balises XPML SANS attribut pitch (validé juillet 2026)
            page_open = b"<xpml><page quantity='0'></xpml>"
            page_cont = b"<xpml></page></xpml><xpml><page quantity='1'></xpml>"

        header = page_open + b"{D" + d_bytes + b"|}" + crlf + page_cont + b"{C|}" + crlf

        raw = image.tobytes()
        inv = bytes(b ^ 0xFF for b in raw)

        # LE SAINT GRAAL (validé sur B-FV4D ET B-EV4) :
        # On envoie UNE UNIQUE commande SG avec H=0300, mais le payload contient
        # la totalité des lignes réelles. Les deux imprimantes ignorent le H et
        # affichent tout d'un bloc -> zéro coupure, zéro ligne blanche.
        comp = self.compress_topix(w_bytes, img_h, inv)
        sg = f"{{SG;0000,0000,{img_w:04d},0300,3,".encode('ascii')
        clen = len(comp)
        sg = sg + bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"

        footer = f"{{XS;I,{quantity:04d},0002C5000|}}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n".encode('ascii')
        return header + sg + footer

    def generate_ticket_tpcl(self, data: TicketData, quantity: int = 1, offset_x: int = 0, offset_y: int = 0, styling: dict = None, xpml_pitch: bool = True) -> str:
        """Génère le flux TPCL de production 3-up.

        xpml_pitch=True  -> B-FV4D (prépa commande)
        xpml_pitch=False -> B-EV4 Gravigny
        """
        image = self._render_toshiba_band([data, data, data], offset_x, offset_y, styling)
        job = self._build_tpcl_job(image, quantity, xpml_pitch=xpml_pitch)
        return job.decode('latin-1')
 
    def generate_separator_tpcl(self, next_product_name: str, xpml_pitch: bool = True) -> str:
        """Génère une étiquette de séparation 3-up graphique."""
        main = Image.new('1', (self.TOSHIBA_CANVAS_W, self.TOSHIBA_CANVAS_H), color=1)
        
        # Etiquette de séparation individuelle (920x224)
        img_w, img_h = 920, 224
        lbl = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(lbl)

        try:
            font = ImageFont.truetype("arialbd.ttf", 60)
        except IOError:
            font = ImageFont.load_default()

        text_to_draw = f">>> {next_product_name} <<<"

        try:
            bbox = draw.textbbox((0, 0), text_to_draw, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(text_to_draw, font=font)

        draw.text((max(0, (img_w - tw) // 2), max(0, (img_h - th) // 2)), text_to_draw, fill=0, font=font)
        lbl_rot = lbl.transpose(Image.ROTATE_90)
        
        x_offsets = [12, 276, 540]
        for i in range(3):
            main.paste(lbl_rot, (x_offsets[i], 0))

        job = self._build_tpcl_job(main, xpml_pitch=xpml_pitch)
        return job.decode('latin-1')

    def generate_ticket_zpl(self, data: TicketData) -> str:
        """Génère le flux ZPL pour une ligne physique (3 étiquettes)."""
        width_dots = self.mm_to_dots(115)
        height_dots = self.mm_to_dots(30)
        
        zpl_parts = [
            "^XA",
            f"^PW{width_dots}",
            f"^LL{height_dots}",
            "^CI27",
        ]

        scale = self.dots_per_mm / 8.0
        
        # Centres physiques réels en mm
        centers_mm = [19.125, 57.375, 95.625]
        centers = [int(c * self.dots_per_mm) for c in centers_mm]

        # Coordonnées et tailles de polices proportionnelles au DPI
        y_lib = int(15 * scale)
        y_barcode = int(45 * scale)
        barcode_h = int(64 * scale)
        y_text = int(115 * scale)
        y_lot = int(155 * scale)

        lib_font_h = int(14 * scale)
        text_font_h = int(11 * scale)
        lot_font_h = int(11 * scale)

        # Chaînes nettoyées
        lib_safe = data.libelle.encode('latin-1', 'ignore').decode('latin-1')
        lot_safe = data.num_lot_display.encode('latin-1', 'ignore').decode('latin-1')
        barcode_text = f"(01){data.gtin}(17){data.date_expiration}(10){data.lot}"

        # Calculer la largeur estimée du code-barres pour le centrage
        barcode_width = self._estimate_barcode_width(data.gtin, data.date_expiration, data.lot)

        for center_x in centers:
            # A. Dessin du libellé produit (centré)
            zpl_parts.append(self._get_zpl_centered_text(lib_safe, center_x, y_lib, lib_font_h))
            
            # B. Code-barres (centré)
            x_barcode = center_x - barcode_width // 2
            zpl_parts.append(f"^FO{x_barcode},{y_barcode}^BY1^BCN,{barcode_h},N,N,N^FD>:>801{data.gtin}17{data.date_expiration}10{data.lot}^FS")
            
            # C. Texte sous le code-barres (centré)
            zpl_parts.append(self._get_zpl_centered_text(barcode_text, center_x, y_text, text_font_h))
            
            # D. Informations de lot (centré)
            zpl_parts.append(self._get_zpl_centered_text(lot_safe, center_x, y_lot, lot_font_h))

        zpl_parts.append("^XZ")
        return "\n".join(zpl_parts)

    def generate_4up_nature_zpl(self, quantity: int) -> str:
        """Génère le flux ZPL pour le layout 4-up (TEC B-EV4) - Yaourt Nature."""
        width_dots = self.mm_to_dots(100)
        height_dots = self.mm_to_dots(43)
        
        scale = self.dots_per_mm / 8.0
        offsets = [int(o * scale) for o in [0, 192, 384, 576]]
        
        zpl_parts = []
        nb_rows = (quantity + 3) // 4
        remaining = quantity

        for r in range(nb_rows):
            to_print = min(4, remaining)
            zpl_parts.append("^XA")
            zpl_parts.append(f"^PW{width_dots}")
            zpl_parts.append(f"^LL{height_dots}")
            zpl_parts.append("^CI28")

            for i in range(to_print):
                x_offset = offsets[i]
                zpl_parts.extend(self._get_nature_label_content_zpl(x_offset))
            
            zpl_parts.append("^XZ")
            remaining -= to_print

        return "\n".join(zpl_parts)

    def generate_4up_nature_tpcl(self, quantity: int) -> str:
        """Génère le flux TPCL (Toshiba Native) pour le layout 4-up (TEC B-EV4)."""
        tpcl_parts = []
        # Initialisation TPCL
        tpcl_parts.append("\x1bAX\x1bAY\x1b{D0430,1000,0380|}\x1bC")
        
        offsets = [0, 192, 384, 576]
        nb_rows = (quantity + 3) // 4
        remaining = quantity

        for r in range(nb_rows):
            to_print = min(4, remaining)
            tpcl_parts.append("\x1bL") # Start label
            
            for i in range(to_print):
                x = offsets[i]
                # Texte "Yaourt Nature"
                tpcl_parts.append(f"\x1bPC001;{x+20:04d},0050,10,10,k,00,B=Yaourt Nature|")
                tpcl_parts.append(f"\x1bPC001;{x+35:04d},0090,08,08,k,00,B=2 x 125gr|")
                # Code EAN-13
                tpcl_parts.append(f"\x1bB00;{x+25:04d},0140,2,2,050,0,0,1,0,3412345678901|")
            
            tpcl_parts.append("\x1bXS\x1bI") # Print & Feed
            remaining -= to_print

        return "".join(tpcl_parts)

    def _get_nature_label_content_zpl(self, x_offset: int) -> list[str]:
        """Contenu ZPL pour l'étiquette Yaourt Nature."""
        scale = self.dots_per_mm / 8.0
        x1 = x_offset + int(20 * scale)
        y1 = int(40 * scale)
        h1 = int(25 * scale)
        
        x2 = x_offset + int(35 * scale)
        y2 = int(70 * scale)
        h2 = int(20 * scale)
        
        x3 = x_offset + int(25 * scale)
        y3 = int(110 * scale)
        h3 = int(50 * scale)
        
        return [
            f"^FO{x1},{y1}^A0N,{h1},{h1}^FDYaourt Nature^FS",
            f"^FO{x2},{y2}^A0N,{h2},{h2}^FD2 x 125gr^FS",
            f"^FO{x3},{y3}^BEN,{h3},Y,N^FD3412345678901^FS"
        ]

    def _estimate_barcode_width(self, gtin: str, date_exp: str, lot: str) -> int:
        """Estime la largeur du code-barres Code 128 (Subset C/B) en modules."""
        # Start C (1) + FNC1 (1) = 2 symboles
        # "01" (2 chiffres) = 1 symbole
        # gtin (14 chiffres) = 7 symboles
        # "17" (2 chiffres) = 1 symbole
        # date_exp (6 chiffres) = 3 symboles
        # "10" (2 chiffres) = 1 symbole
        num_symbols = 2 + 1 + 7 + 1 + 3 + 1
        
        # Encodage du lot
        if lot.isdigit():
            n = len(lot)
            if n % 2 == 0:
                num_symbols += n // 2
            else:
                num_symbols += (n // 2) + 2
        else:
            try:
                first_letter_idx = next(i for i, c in enumerate(lot) if c.isalpha())
            except StopIteration:
                first_letter_idx = len(lot)
            
            pre_digits = first_letter_idx
            if pre_digits % 2 == 0:
                num_symbols += pre_digits // 2
            else:
                num_symbols += (pre_digits // 2) + 2
                
            num_symbols += 1 # Switch vers Code B
            num_symbols += len(lot) - first_letter_idx
            
        # Total modules = symboles * 11 + 13 (Stop)
        total_modules = num_symbols * 11 + 13
        return total_modules

    def _get_zpl_centered_text(self, text: str, center_x: int, y: int, font_h: int) -> str:
        """Génère la commande ZPL de texte centré sur la largeur d'une étiquette."""
        width = int(32 * self.dots_per_mm)
        x_start = center_x - width // 2
        if x_start < 0:
            x_start = 0
        return f"^FO{x_start},{y}^A0N,{font_h},{font_h}^FB{width},1,0,C^FD{text}^FS"

    def _draw_4up_toshiba_single_label(self, nom: str, ean13: str, styling: dict = None, label_h: int = 176, nom_impression: str = None) -> Image.Image:
        """Dessine une étiquette 4-up et la pivote."""
        styling = styling or {}
        img_w, img_h = 344, label_h
        img = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(img)
        
        nom_imp = nom_impression if nom_impression else nom
        
        try:
            t_font = "arialbd.ttf" if styling.get("title_bold") else "arial.ttf"
            g_font = "arialbd.ttf" if styling.get("gs1_bold") else "arial.ttf"
            
            font_title = ImageFont.truetype(t_font, max(10, 22 + styling.get("title_size", 0)))
            font_ean   = ImageFont.truetype(g_font, max(10, 22 + styling.get("gs1_size", 0)))
        except IOError:
            font_title = ImageFont.load_default()
            font_ean   = ImageFont.load_default()

        # Nom de l'étiquette (Gestion RGF via extraction du graphique du .prn)
        is_rgf = "RGF" in nom_imp.upper()
        is_figue_rgf = (ean13 == "3374270040521")  # La Figue a un rendu complètement custom
        
        if is_rgf and not is_figue_rgf:
            import re, zlib, base64
            from pathlib import Path
            from src.config import base_path
            
            prn_name = nom_imp.upper().replace("RGF", "").strip().lower() + ".prn"
            prn_path = base_path / "fichierprn" / prn_name
            prn_graphic_pasted = False
            
            if prn_path.exists():
                with open(prn_path, "rb") as f:
                    data = f.read()
                match = re.search(b'\^GFA,(\d+),(\d+),(\d+),:Z64:(.*?)\^FS', data, re.DOTALL)
                if match:
                    uncomp = int(match.group(2))
                    row = int(match.group(3))
                    b64 = match.group(4).replace(b'\r', b'').replace(b'\n', b'')
                    if b64[-4:].isalnum(): b64 = b64[:-4]
                    compressed = base64.b64decode(b64)
                    uncompressed = zlib.decompress(compressed)
                    
                    inverted = bytes(~b & 255 for b in uncompressed)
                    prn_img = Image.frombytes('1', (row*8, uncomp//row), inverted)
                    bbox = prn_img.getbbox()
                    if bbox: prn_img = prn_img.crop(bbox)
                    
                    # On s'assure qu'elle ne dépasse pas (au cas où)
                    if prn_img.width > img_w - 4:
                        prn_img = prn_img.resize((img_w - 4, int(prn_img.height * ((img_w - 4)/prn_img.width))), Image.NEAREST)
                        
                    img.paste(prn_img, ((img_w - prn_img.width) // 2, 5))
                    prn_graphic_pasted = True
                    
            if not prn_graphic_pasted:
                # Fallback
                title_w = draw.textlength(nom_imp, font=font_title)
                draw.text(((img_w - title_w) // 2, 5), nom_imp, font=font_title, fill=0)
        elif not is_figue_rgf:
            # Parfum classique
            title_w = draw.textlength(nom_imp, font=font_title)
            draw.text(((img_w - title_w) // 2, 5), nom_imp, font=font_title, fill=0)

        # Code-barres ou QR Code
        # Détection spéciale pour la Figue RGF (qui utilise un QR Code GS1 Digital Link)
        if ean13 == "3374270040521":
            # --- Figue RGF : libellé en haut, QR code au centre, EAN en bas ---
            header_text = "RGF FIGUE 2x125g"
            tw = draw.textlength(header_text, font=font_title)
            draw.text(((img_w - tw) // 2, 5), header_text, font=font_title, fill=0)
            
            import qrcode
            qr = qrcode.QRCode(version=2, box_size=3, border=0)
            qr.add_data(f"qrrelai.fr/01/0{ean13}")
            qr.make(fit=True)
            bc_img = qr.make_image(fill_color="black", back_color="white").convert('1')
            
            # QR code centré entre le texte du haut et le texte du bas
            qr_y = (label_h - bc_img.height) // 2
            img.paste(bc_img, ((img_w - bc_img.width)//2, max(30, qr_y)))
            
            # EAN numérique en bas (on garde le numéro court, pas celui qui commence par 01/)
            if len(ean13) == 13:
                ean_spaced = f"{ean13[0]} {ean13[1:7]} {ean13[7:13]}"
            else:
                ean_spaced = ean13
                
            tw = draw.textlength(ean_spaced, font=font_ean)
            draw.text(((img_w - tw) // 2, label_h - 30), ean_spaced, font=font_ean, fill=0)
        else:
            # Code-barres EAN-13 standard
            stream = io.BytesIO()
            fp = barcode.get('ean13', ean13, writer=ImageWriter())
            fp.write(stream, options={
                'dpi': 203,
                'module_width': 0.375,
                'module_height': 12.0,
                'quiet_zone': 2.0,
                'write_text': False
            })
            stream.seek(0)
            bc_img = Image.open(stream).convert('1')
            
            bc_img = bc_img.point(lambda p: p > 128 and 255)
            img.paste(bc_img, ((img_w - bc_img.width)//2, 32))
            
            if len(ean13) == 13:
                ean_spaced = f"{ean13[0]} {ean13[1:7]} {ean13[7:13]}"
            else:
                ean_spaced = ean13
                
            tw = draw.textlength(ean_spaced, font=font_ean)
            ean_y = label_h - 36
            draw.text(((img_w - tw) // 2, ean_y), ean_spaced, font=font_ean, fill=0)
        
        return img.transpose(Image.ROTATE_90)

    def _render_4up_toshiba_band(self, nom: str, ean13: str, offset_x: int = 0, offset_y: int = 0, styling: dict = None, bev4: bool = False, nom_impression: str = None) -> Image.Image:
        """Genere la bande de 4 etiquettes cote a cote pour la Toshiba."""
        if bev4:
            canvas_w, canvas_h = 768, 360
            x_offsets = [0, 200, 400, 600]
            label_h = 168
        else:
            canvas_w, canvas_h = 800, 344
            x_offsets = [0, 200, 400, 600]
            label_h = 176

        main = Image.new('1', (canvas_w, canvas_h), color=1)

        for i in range(4):
            lbl_rot = self._draw_4up_toshiba_single_label(nom, ean13, styling, label_h=label_h, nom_impression=nom_impression)
            x = x_offsets[i] + offset_x
            y = offset_y
            # Securite : ne pas coller en dehors du canvas
            if 0 <= x < canvas_w:
                main.paste(lbl_rot, (x, y))

        return main

    def generate_4up_toshiba_tpcl(self, parfum: dict, nb_rows: int, offset_x: int = 0, offset_y: int = 0, styling: dict = None, xpml_pitch: bool = True, d_param: str = None) -> str:
        """Genere le flux TPCL de production 4-up pour Toshiba."""
        parfum_name = parfum['nom']
        ean13 = parfum['ean13']
        nom_impression = parfum.get('nom_impression')

        is_bev4 = not xpml_pitch
        image = self._render_4up_toshiba_band(parfum_name, ean13, offset_x, offset_y, styling, bev4=is_bev4, nom_impression=nom_impression)

        job = self._build_tpcl_job(image, quantity=nb_rows, xpml_pitch=xpml_pitch, d_param=d_param)
        return job.decode('latin-1')

    def _render_4up_separator_band(self, next_product_name: str, bev4: bool = False) -> Image.Image:
        """Dessine une bande de séparation graphique pour le rouleau 4-up (Toshiba)."""
        if bev4:
            canvas_w, canvas_h = 768, 360
        else:
            canvas_w, canvas_h = 800, 344

        img = Image.new('1', (canvas_w, canvas_h), color=1)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arialbd.ttf", 60)
        except IOError:
            font = ImageFont.load_default()
            
        text_to_draw = f">>> {next_product_name} <<<"
        
        try:
            bbox = draw.textbbox((0, 0), text_to_draw, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(text_to_draw, font=font)
            
        draw.text((max(0, (canvas_w - tw) // 2), max(0, (canvas_h - th) // 2)), text_to_draw, fill=0, font=font)
        
        # Lignes horizontales pour bien délimiter
        line_thick = 4
        draw.rectangle([0, 20, canvas_w, 20 + line_thick], fill=0)
        draw.rectangle([0, canvas_h - 20 - line_thick, canvas_w, canvas_h - 20], fill=0)
        
        return img

    def generate_separator_4up_tpcl(self, next_product_name: str, xpml_pitch: bool = True, d_param: str = None) -> str:
        """Génère le flux TPCL de séparation pour la ligne 4-up Toshiba."""
        is_bev4 = not xpml_pitch
        image = self._render_4up_separator_band(next_product_name, bev4=is_bev4)
        job = self._build_tpcl_job(image, quantity=1, xpml_pitch=xpml_pitch, d_param=d_param)
        return job.decode('latin-1')

    def image_to_zebra_gfa(self, image: Image.Image, x_pos: int, y_pos: int) -> str:
        """
        Convertit une image Pillow (mode '1') en commande ZPL ^GFA (Graphic Field) avec encodage Hex.
        C'est l'équivalent direct du flux binaire envoyé par les drivers Windows.
        """
        if image.mode != '1':
            image = image.convert('1')
            
        img_w, img_h = image.size
        bytes_per_row = (img_w + 7) // 8
        
        # S'assurer que l'image est un multiple de 8 en largeur pour un alignement parfait des octets
        if img_w % 8 != 0:
            padded = Image.new('1', (bytes_per_row * 8, img_h), color=1)
            padded.paste(image, (0, 0))
            image = padded
            
        raw = image.tobytes()
        # Inversion des bits : Pillow (0=Noir, 255=Blanc) -> tobytes(0=Noir)
        # ZPL attend : 1=Noir, 0=Blanc. Donc on inverse avec un XOR 0xFF
        inv = bytes(b ^ 0xFF for b in raw)
        
        # Encodage en Hexadécimal ASCII
        hex_str = inv.hex().upper()
        total_bytes = len(inv)
        
        # Construction de la commande finale ZPL
        zpl = (
            f"^XA\n"
            f"^FO{x_pos},{y_pos}\n"
            f"^GFA,{total_bytes},{total_bytes},{bytes_per_row},{hex_str}\n"
            f"^PQ1,0,1,Y\n"
            f"^XZ"
        )
        return zpl

    def _draw_zebra_single_label_1up(self, data: TicketData, styling: dict = None) -> Image.Image:
        """Dessine une étiquette individuelle Zebra (115x30mm) en paysage puis la pivote."""
        styling = styling or {}
        img_w, img_h = 1144, 352
        img = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(img)
        
        try:
            t_font = "arialbd.ttf" if styling.get("title_bold") else "arial.ttf"
            g_font = "arialbd.ttf" if styling.get("gs1_bold") else "arial.ttf"
            l_font = "arialbd.ttf" if styling.get("lot_bold") else "arial.ttf"
            
            font_title  = ImageFont.truetype(t_font, max(10, 45 + styling.get("title_size", 0)))
            font_normal = ImageFont.truetype(l_font, max(10, 25 + styling.get("lot_size", 0)))
            font_small  = ImageFont.truetype(g_font, max(10, 25 + styling.get("gs1_size", 0)))
        except IOError:
            font_title  = ImageFont.load_default()
            font_normal = ImageFont.load_default()
            font_small  = ImageFont.load_default()

        # Libellé (collé en haut)
        libelle = data.libelle.encode('latin-1', 'ignore').decode('latin-1')
        try:
            bbox = draw.textbbox((0, 0), libelle, font=font_title)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(libelle, font=font_title)
        draw.text(((img_w - tw)//2, 5), libelle, fill=0, font=font_title)

        # Code-barres
        barcode_y = 50
        barcode_data = f"01{data.gtin}17{data.date_expiration}10{data.lot}"
        stream = io.BytesIO()
        fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
        fp.write(stream, options={
            'dpi': 300,
            'module_width': 0.35,
            'module_height': 15.0,
            'quiet_zone': 2.0,
            'write_text': False,
        })
        stream.seek(0)
        bc_img = Image.open(stream).convert('1')
        img.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
        barcode_bottom = barcode_y + bc_img.height

        # Texte sous code-barres
        gs1_text = f"(01){data.gtin}(17){data.date_expiration}(10){data.lot}"
        try:
            bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(gs1_text, font=font_small)
        draw.text(((img_w - tw)//2, barcode_bottom + 5), gs1_text, fill=0, font=font_small)

        # Lot et DLC (agrandi et positionné juste en dessous)
        lot_text = data.num_lot_display.encode('latin-1', 'ignore').decode('latin-1')
        try:
            bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw, _ = draw.textsize(lot_text, font=font_normal)
        draw.text(((img_w - tw)//2, barcode_bottom + 40), lot_text, fill=0, font=font_normal)
        
        # Zebra attend l'image pivotée (352 de large x 1144 de haut)
        return img.transpose(Image.ROTATE_90)
        
    def generate_ticket_zebra_300(self, data: TicketData, offset_x: int = 800, offset_y: int = 18, styling: dict = None) -> str:
        """Génère le flux ZPL graphique complet pour la Zebra 300 DPI (Prépa Commande)"""
        img = self._draw_zebra_single_label_1up(data, styling)
        return self.image_to_zebra_gfa(img, offset_x, offset_y)

    def generate_separator_zebra_300(self, next_product_name: str, offset_x: int = 800, offset_y: int = 18) -> str:
        """Génère le séparateur ZPL graphique pour la Zebra 300 DPI"""
        img_w, img_h = 1144, 352
        lbl = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(lbl)
        try:
            font = ImageFont.truetype("arialbd.ttf", 80)
        except IOError:
            font = ImageFont.load_default()

        text_to_draw = f">>> {next_product_name} <<<"
        try:
            bbox = draw.textbbox((0, 0), text_to_draw, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(text_to_draw, font=font)

        draw.text((max(0, (img_w - tw) // 2), max(0, (img_h - th) // 2)), text_to_draw, fill=0, font=font)
        
        lbl_rot = lbl.transpose(Image.ROTATE_90)
        return self.image_to_zebra_gfa(lbl_rot, offset_x, offset_y)

    def generate_ticket_zebra_203_pots(self, nom: str, ean13: str, quantity: int = 1) -> str:
        """Génère le flux ZPL natif pour les étiquettes Pots x2 (2-up) sur la Zebra 203 DPI."""
        import unicodedata
        import re
        from pathlib import Path
        from src.config import base_path
        
        # GESTION SPECIALE POUR "RGF" (Utilisation des PRN bruts fournis par le client)
        if "RGF" in nom.upper():
            # Ex: "Vanille RGF" -> "vanille.prn"
            prn_name = nom.upper().replace("RGF", "").strip().lower() + ".prn"
            prn_path = base_path / "fichierprn" / prn_name
            if prn_path.exists():
                with open(prn_path, "rb") as f:
                    # Lecture en latin-1 pour préserver les éventuels octets binaires du spooler Windows (\x1b...)
                    raw_prn = f.read().decode("latin-1")
                # Remplacer la quantité ^PQ1 (ou autre) par la quantité désirée
                flux = re.sub(r'\^PQ\d+', f'^PQ{quantity}', raw_prn)
                return flux
            else:
                import logging
                logging.getLogger(__name__).warning(f"Fichier PRN introuvable pour {nom} ({prn_path}). Fallback sur le moteur ZPL classique.")

        # Normalisation propre pour le texte classique
        nom_clean = unicodedata.normalize('NFD', nom).encode('ascii', 'ignore').decode('utf-8')
        zpl = f"""^XA
^CI28
^FO92,16^A0N,25,25^FD{nom_clean}^FS
^BY2,2,56^FT122,106^BEN,,Y,N^FD{ean13}^FS
^FO540,16^A0N,25,25^FD{nom_clean}^FS
^BY2,2,56^FT565,106^BEN,,Y,N^FD{ean13}^FS
^PQ{quantity},0,1,Y
^XZ
"""
        return zpl

    def generate_zebra_1up_preview_png(self, data: TicketData, styling: dict = None) -> bytes:
        """Génère l'aperçu PNG de l'étiquette Zebra 1-up pour la calibration visuelle."""
        img = self._draw_zebra_single_label_1up(data, styling)
        # L'image renvoyée est en portrait (352x1144) pour l'impression ZPL.
        # On la remet en mode paysage (1144x352) pour l'affichage web.
        img = img.transpose(Image.ROTATE_270)
        stream = io.BytesIO()
        img.save(stream, format='PNG')
        return stream.getvalue()

    def generate_4up_preview_png(self, parfum: dict) -> bytes:
        """Génère l'aperçu PNG pour l'interface Web d'une seule étiquette 4-up."""
        lbl_rot = self._draw_4up_toshiba_single_label(parfum['nom'], parfum['ean13'], nom_impression=parfum.get('nom_impression'))
        # L'image est retournée à 90° (176x344) pour l'imprimante.
        # On la remet en mode paysage (344x176) pour l'aperçu Web.
        img = lbl_rot.transpose(Image.ROTATE_270)
        
        # Agrandissement x2 pour la netteté sur l'écran
        img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate_3up_band_preview_png(self, data: TicketData, styling: dict = None) -> bytes:
        """Génère l'aperçu PNG de la bande complète 3-up pour la calibration visuelle."""
        img = self._render_toshiba_band([data, data, data], styling=styling)
        img = img.transpose(Image.ROTATE_270)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate_4up_band_preview_png(self, parfum: dict, styling: dict = None) -> bytes:
        """Génère l'aperçu PNG de la bande complète 4-up pour la calibration visuelle."""
        img = self._render_4up_toshiba_band(parfum['nom'], parfum['ean13'], styling=styling, nom_impression=parfum.get('nom_impression'))
        img = img.transpose(Image.ROTATE_270)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def generate_zebra_2up_preview_png(self, parfum: dict, styling: dict = None) -> bytes:
        """Génère l'aperçu PNG pour la calibration de la bobine 2-up Zebra (203dpi)."""
        lbl_rot = self._draw_4up_toshiba_single_label(parfum.get('nom', 'Yaourt Fraise'), parfum.get('ean13', '3412345678918'), styling, nom_impression=parfum.get('nom_impression'))
        lbl_flat = lbl_rot.transpose(Image.ROTATE_270)
        
        gap = 24
        w, h = lbl_flat.width, lbl_flat.height
        canvas = Image.new('1', (w * 2 + gap, h), color=1)
        canvas.paste(lbl_flat, (0, 0))
        canvas.paste(lbl_flat, (w + gap, 0))
        
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue()

