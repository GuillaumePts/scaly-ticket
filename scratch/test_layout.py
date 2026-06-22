import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter

def draw_single_label(libelle, gtin, date_expiration, lot) -> Image.Image:
    img_w, img_h = 920, 240
    img = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(img)
    
    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 38)
        font_normal = ImageFont.truetype("arialbd.ttf", 32)
        font_small  = ImageFont.truetype("arialbd.ttf", 28)
    except IOError:
        font_title  = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small  = ImageFont.load_default()

    libelle_safe = libelle.encode('latin-1', 'ignore').decode('latin-1')
    try:
        bbox = draw.textbbox((0, 0), libelle_safe, font=font_title)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(libelle_safe, font=font_title)
    draw.text(((img_w - tw)//2, 10), libelle_safe, fill=0, font=font_title)

    barcode_y = 60
    barcode_data = f"01{gtin}17{date_expiration}10{lot}"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.375,
        'module_height': 15.0,
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    img.paste(bc_img, ((img_w - bc_img.width)//2, barcode_y))
    barcode_bottom = barcode_y + bc_img.height

    gs1_text = f"(01){gtin}(17){date_expiration}(10){lot}"
    try:
        bbox = draw.textbbox((0, 0), gs1_text, font=font_small)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(gs1_text, font=font_small)
    draw.text(((img_w - tw)//2, barcode_bottom + 10), gs1_text, fill=0, font=font_small)

    lot_text = f"DLC {date_expiration} LOT {lot}"
    try:
        bbox = draw.textbbox((0, 0), lot_text, font=font_normal)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(lot_text, font=font_normal)
    draw.text(((img_w - tw)//2, barcode_bottom + 45), lot_text, fill=0, font=font_normal)
    
    return img

if __name__ == '__main__':
    img = draw_single_label("6 Yaourt Brassé Coco 140G RGF - 140G", "13374270830099", "260712", "26L222805")
    img.save("scratch_label.png")
    print("Label saved to scratch_label.png")
