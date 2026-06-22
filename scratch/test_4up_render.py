import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def draw_4up_single_label(parfum_name: str, ean13: str) -> Image.Image:
    # 43mm x 21mm at 8 dots/mm
    img_w, img_h = 344, 168
    img = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Parfum
    try:
        bbox = draw.textbbox((0, 0), parfum_name, font=font_title)
        tw = bbox[2] - bbox[0]
    except AttributeError:
        tw, _ = draw.textsize(parfum_name, font=font_title)
    draw.text(((img_w - tw)//2, 10), parfum_name, fill=0, font=font_title)

    # Barcode EAN-13
    stream = io.BytesIO()
    # We use ean13
    fp = barcode.get('ean13', ean13, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': 0.375,
        'module_height': 8.0,
        'quiet_zone': 2.0,
        'write_text': True,
        'text_distance': 3.0,
        'font_size': 8
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    
    # Scale down if barcode is too big for the label
    if bc_img.width > img_w - 20:
        ratio = (img_w - 20) / bc_img.width
        bc_img = bc_img.resize((int(bc_img.width * ratio), int(bc_img.height * ratio)), Image.LANCZOS)
    
    # Threshold after resize
    bc_img = bc_img.point(lambda p: p > 128 and 255)
    
    img.paste(bc_img, ((img_w - bc_img.width)//2, 50))
    
    return img.transpose(Image.ROTATE_90)

def render_4up_band(parfum_name: str, ean13: str) -> Image.Image:
    TOSHIBA_CANVAS_W = 768
    # 45mm pitch -> 360 dots
    canvas_h = 360 
    main = Image.new('1', (TOSHIBA_CANVAS_W, canvas_h), color=1)
    
    x_offsets = [18, 202, 386, 570]
    for x in x_offsets:
        lbl = draw_4up_single_label(parfum_name, ean13)
        main.paste(lbl, (x, 0))
    return main

main_img = render_4up_band("Yaourt Nature", "3412345678901")
main_img.save("scratch/test_4up_preview.png")
print("Image saved to scratch/test_4up_preview.png")
