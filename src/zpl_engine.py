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

    def _draw_toshiba_single_label(self, data: TicketData) -> Image.Image:
        """Dessine une étiquette individuelle (115x30mm) en paysage puis la pivote."""
        img_w, img_h = 920, 240
        img = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(img)
        
        try:
            # Polices plus fines et plus petites pour alléger le poids en mémoire (TOSHIBA_CHUNK_H)
            font_title  = ImageFont.truetype("arial.ttf", 28)
            font_normal = ImageFont.truetype("arial.ttf", 20)
            font_small  = ImageFont.truetype("arial.ttf", 20)
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

    def _render_toshiba_band(self, data_list: list) -> Image.Image:
        """Génère la bande complète 3-up (Canvas 800x1200)."""
        # Assemblage sur le canvas global 3-up
        main = Image.new('1', (self.TOSHIBA_CANVAS_W, self.TOSHIBA_CANVAS_H), color=1)
        
        x_offsets = [12, 268, 524]
        for i, data in enumerate(data_list[:3]):
            lbl = self._draw_toshiba_single_label(data)
            main.paste(lbl, (x_offsets[i], 0))
        return main

    def _build_tpcl_job(self, image: Image.Image) -> bytes:
        img_w, img_h = image.size
        w_bytes = img_w // 8
        
        header = (
            b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
            b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
        )
        
        raw = image.tobytes()
        inv = bytes(b ^ 0xFF for b in raw)
        
        # Compression de la TOTALITÉ de l'image (1200 lignes)
        comp = self.compress_topix(w_bytes, img_h, inv)
        
        # LE SAINT GRAAL :
        # L'analyse binaire du driver officiel montre que la machine accepte d'imprimer
        # bien plus que 300 lignes, à UNE SEULE condition : que le paramètre H de la 
        # commande SG soit strictement <= 0300 (sinon l'analyseur de syntaxe plante = voyant rouge).
        # On envoie donc UNE UNIQUE commande SG avec H=0300, mais on lui donne un payload
        # qui contient nos 1200 lignes ! Le décompresseur de la machine ignorera le H=0300 
        # et affichera tout d'un bloc. Résultat : zéro coupure !
        sg = f"{{SG;0000,0000,{img_w:04d},0300,3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        
        footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
        return header + sg + footer

    def generate_ticket_tpcl(self, data: TicketData) -> str:
        """Génère le flux TPCL de production 3-up pour la Toshiba B-FV4D."""
        # On passe 3 fois la même donnée pour imprimer les 3 étiquettes de la rangée
        image = self._render_toshiba_band([data, data, data])
        job = self._build_tpcl_job(image)
        return job.decode('latin-1')
 
    def generate_separator_tpcl(self, next_product_name: str) -> str:
        """Génère une étiquette de séparation 3-up graphique."""
        main = Image.new('1', (self.TOSHIBA_CANVAS_W, self.TOSHIBA_CANVAS_H), color=1)
        
        # Etiquette de séparation individuelle (920x240)
        img_w, img_h = 920, 240
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
        
        x_offsets = [12, 268, 524]
        for i in range(3):
            main.paste(lbl_rot, (x_offsets[i], 0))

        job = self._build_tpcl_job(main)
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

    def _draw_4up_toshiba_single_label(self, parfum_name: str, ean13: str) -> Image.Image:
        """Dessine une étiquette 4-up (43x22mm -> 344x176 dots) et la pivote."""
        img_w, img_h = 344, 176
        img = Image.new('1', (img_w, img_h), color=1)
        draw = ImageDraw.Draw(img)
        
        try:
            font_title = ImageFont.truetype("arial.ttf", 22)
        except IOError:
            font_title = ImageFont.load_default()

        # Texte (Centré en haut, marge de 5)
        title_w = draw.textlength(parfum_name, font=font_title)
        draw.text(((img_w - title_w) // 2, 5), parfum_name, font=font_title, fill=0)

        # Code-barres EAN-13
        stream = io.BytesIO()
        fp = barcode.get('ean13', ean13, writer=ImageWriter())
        fp.write(stream, options={
            'dpi': 203,
            'module_width': 0.40,
            'module_height': 12.0,
            'quiet_zone': 2.0,
            'write_text': False
        })
        stream.seek(0)
        bc_img = Image.open(stream).convert('1')
        
        # Le code-barres généré a une taille naturelle qui rentre sans redimensionnement
        bc_img = bc_img.point(lambda p: p > 128 and 255)
        # On le place à y=32 pour ne pas écraser le texte
        img.paste(bc_img, ((img_w - bc_img.width)//2, 32))
        
        # Texte manuel du code-barre formaté avec espaces
        if len(ean13) == 13:
            ean_spaced = f"{ean13[0]} {ean13[1:7]} {ean13[7:13]}"
        else:
            ean_spaced = ean13
            
        try:
            font_bc = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font_bc = ImageFont.load_default()
            
        tw = draw.textlength(ean_spaced, font=font_bc)
        draw.text(((img_w - tw) // 2, 140), ean_spaced, font=font_bc, fill=0)
        
        return img.transpose(Image.ROTATE_90)

    def _render_4up_toshiba_band(self, parfum_name: str, ean13: str) -> Image.Image:
        """Génère la bande 4-up complète de largeur 800 et de hauteur 344."""
        canvas_h = 344 
        main = Image.new('1', (800, canvas_h), color=1)
        
        # 4 étiquettes de 176 dots de large (22mm) avec 24 dots (~3mm) d'espacement.
        # On retire la marge gauche de 12 dots car l'imprimante a déjà un décalage physique.
        x_offsets = [0, 200, 400, 600]
        for x in x_offsets:
            lbl = self._draw_4up_toshiba_single_label(parfum_name, ean13)
            main.paste(lbl, (x, 0))
            
        return main

    def generate_4up_toshiba_tpcl(self, parfum: dict, quantity: int) -> str:
        """Génère le flux binaire TPCL (Raster Mode) pour l'impression 4-up."""
        # Nombre de lignes physiques (4 étiquettes par ligne)
        nb_rows = (quantity + 3) // 4
        
        parfum_name = parfum['nom']
        ean13 = parfum['ean13']
        
        # On génère l'image de la ligne
        image = self._render_4up_toshiba_band(parfum_name, ean13)
        img_w, img_h = image.size
        w_bytes = img_w // 8
        
        # On utilise le même trick que le 3-up : D1221,0975,1201| car physiquement 
        # le capteur de la machine reste calibré sur 120.1mm de hauteur.
        # Mais le {C|} efface le buffer. 
        header = (
            b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
            b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
        )
        
        raw = image.tobytes()
        inv = bytes(b ^ 0xFF for b in raw)
        
        # On compresse 1 rangée (344 lignes)
        comp = self.compress_topix(w_bytes, img_h, inv)
        
        # Commande SG : H=0300 (Fake height to bypass memory crash), payload = 344 lignes réelles.
        sg = f"{{SG;0000,0000,{img_w:04d},0300,3,".encode('ascii')
        
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        
        # On répète la rangée nb_rows fois avec XS;I,xxxx
        footer = f"{{XS;I,{nb_rows:04d},0002C5000|}}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n".encode('ascii')
        
        job = header + sg + footer
        return job.decode('latin-1')

    def generate_4up_preview_png(self, parfum: dict) -> bytes:
        """Génère l'aperçu PNG pour l'interface Web d'une seule étiquette 4-up."""
        lbl_rot = self._draw_4up_toshiba_single_label(parfum['nom'], parfum['ean13'])
        # L'image est retournée à 90° (176x344) pour l'imprimante.
        # On la remet en mode paysage (344x176) pour l'aperçu Web.
        img = lbl_rot.transpose(Image.ROTATE_270)
        
        # Agrandissement x2 pour la netteté sur l'écran
        img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

