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
                for l1 in range(8):
                    for l2 in range(9):
                        for l3 in range(9):
                            val = line_arr[l1][l2][l3]
                            if val != 0:
                                comp_buffer.append(val)
            
            last_line = bytearray(line_data)
            
        # Strip trailing zero bytes (empty lines at the end of the image) to match driver behavior
        while len(comp_buffer) > 0 and comp_buffer[-1] == 0:
            comp_buffer.pop()
            
        return bytes(comp_buffer)

    def generate_ticket_tpcl(self, data: TicketData) -> str:
        """Génère le flux TPCL graphique compressé en TOPIX pour la Toshiba B-FV4D (Hauteur 240, 3-up)."""
        width_dots = 832
        height_dots = 240
        
        # 1. Dessin de l'étiquette avec Pillow
        image = Image.new('1', (width_dots, height_dots), color=1) # 1 = Fond blanc
        draw = ImageDraw.Draw(image)
        
        # Chargement des polices
        try:
            font_libelle = ImageFont.truetype("arial.ttf", 14)
            font_barcode_text = ImageFont.truetype("arial.ttf", 11)
            font_bold = ImageFont.truetype("arialbd.ttf", 11)
        except IOError:
            font_libelle = ImageFont.load_default()
            font_barcode_text = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            
        # Nettoyage des chaînes
        lib_safe = data.libelle.encode('latin-1', 'ignore').decode('latin-1')
        lot_safe = data.num_lot_display.encode('latin-1', 'ignore').decode('latin-1')
        
        # 2. Génération du code-barres GS1-128 avec options DPI 203 adaptées (sans parenthèses dans le code-barres)
        barcode_data_stripped = f"01{data.gtin}17{data.date_expiration}10{data.lot}"
        stream = io.BytesIO()
        fp = barcode.get('gs1_128', barcode_data_stripped, writer=ImageWriter())
        fp.write(stream, options={
            'dpi': 203,
            'module_width': 0.13,  # 1 dot module width
            'module_height': 8.0,  # 64 dots height
            'quiet_zone': 1.0,     # 8 dots quiet zone
            'write_text': False
        })
        stream.seek(0)
        
        barcode_img = Image.open(stream).convert('1')
        
        # 3. Dessin des 3 colonnes side-by-side centrées sur les labels physiques
        # Les centres physiques relatifs au printhead de 104mm (832 dots) sont 109, 415, 721
        centers = [109, 415, 721]
        
        for center_x in centers:
            # A. Dessin du libellé produit (centré)
            try:
                left, top, right, bottom = draw.textbbox((0, 0), lib_safe, font=font_libelle)
                lib_width = right - left
            except AttributeError:
                lib_width, _ = draw.textsize(lib_safe, font=font_libelle)
            x_lib = center_x - lib_width // 2
            draw.text((x_lib, 15), lib_safe, fill=0, font=font_libelle)
            
            # B. Collage du code-barres (centré)
            x_barcode = center_x - barcode_img.width // 2
            image.paste(barcode_img, (x_barcode, 45))
            
            # C. Dessin du texte sous le code-barres (avec parenthèses, centré)
            barcode_text = f"(01){data.gtin}(17){data.date_expiration}(10){data.lot}"
            try:
                left, top, right, bottom = draw.textbbox((0, 0), barcode_text, font=font_barcode_text)
                text_width = right - left
            except AttributeError:
                text_width, _ = draw.textsize(barcode_text, font=font_barcode_text)
            x_text = center_x - text_width // 2
            draw.text((x_text, 115), barcode_text, fill=0, font=font_barcode_text)
            
            # D. Informations de lot (centré)
            try:
                left, top, right, bottom = draw.textbbox((0, 0), lot_safe, font=font_bold)
                lot_width = right - left
            except AttributeError:
                lot_width, _ = draw.textsize(lot_safe, font=font_bold)
            x_lot = center_x - lot_width // 2
            draw.text((x_lot, 155), lot_safe, fill=0, font=font_bold)
            
        # 4. Inversion pour la Toshiba (0=blanc, 1=noir)
        raw = image.tobytes()
        inverted_raw = bytes(b ^ 0xFF for b in raw)
        
        # 5. Compression TOPIX (Mode 3)
        w_bytes = width_dots // 8
        compressed = self.compress_topix(w_bytes, height_dots, inverted_raw)
        
        # 6. Assemblage du flux TPCL
        len_val = len(compressed)
        belen = bytes([len_val >> 8, len_val & 0xFF])
        crlf = b"\r\n"
        
        header = (
            b"<xpml><page quantity='0' pitch='30.0 mm'></xpml>" +
            b"{D1040,0300,0300|}" + crlf +
            b"<xpml></page></xpml>" +
            b"<xpml><page quantity='1' pitch='30.0 mm'></xpml>" +
            b"{C|}" + crlf
        )
        sg_command = f"{{SG;0000,0000,{width_dots:04d},{height_dots:04d},3,".encode('ascii') + belen + compressed + b"|}" + crlf
        footer = (
            b"{XS;I,0001,0000C5000|}" + crlf +
            b"<xpml></page></xpml><xpml><end/></xpml>"
        )
        
        job = header + sg_command + footer
        return job.decode('latin-1')
 
    def generate_separator_tpcl(self, next_product_name: str) -> str:
        """Génère une étiquette de séparation graphique compressée en TOPIX pour la Toshiba B-FV4D (Hauteur 240)."""
        width_dots = 832
        height_dots = 240
        
        image = Image.new('1', (width_dots, height_dots), color=1)
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arialbd.ttf", 36)
        except IOError:
            font = ImageFont.load_default()
            
        text_to_draw = f">>> {next_product_name} <<<"
        
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text_to_draw, font=font)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            text_width, text_height = draw.textsize(text_to_draw, font=font)
            
        x = max(0, (width_dots - text_width) // 2)
        y = max(0, (height_dots - text_height) // 2)
        
        draw.text((x, y), text_to_draw, fill=0, font=font)
        
        raw = image.tobytes()
        inverted_raw = bytes(b ^ 0xFF for b in raw)
        
        w_bytes = width_dots // 8
        compressed = self.compress_topix(w_bytes, height_dots, inverted_raw)
        
        len_val = len(compressed)
        belen = bytes([len_val >> 8, len_val & 0xFF])
        crlf = b"\r\n"
        
        header = (
            b"<xpml><page quantity='0' pitch='30.0 mm'></xpml>" +
            b"{D1040,0300,0300|}" + crlf +
            b"<xpml></page></xpml>" +
            b"<xpml><page quantity='1' pitch='30.0 mm'></xpml>" +
            b"{C|}" + crlf
        )
        sg_command = f"{{SG;0000,0000,{width_dots:04d},{height_dots:04d},3,".encode('ascii') + belen + compressed + b"|}" + crlf
        footer = (
            b"{XS;I,0001,0000C5000|}" + crlf +
            b"<xpml></page></xpml><xpml><end/></xpml>"
        )
        
        job = header + sg_command + footer
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
