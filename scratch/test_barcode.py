import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def create_barcode(module_width):
    barcode_data = "0113374270830099172607121026L222805"
    stream = io.BytesIO()
    fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
    fp.write(stream, options={
        'dpi': 203,
        'module_width': module_width,
        'module_height': 15.0,
        'quiet_zone': 2.0,
        'write_text': False,
    })
    stream.seek(0)
    bc_img = Image.open(stream).convert('1')
    return bc_img

if __name__ == '__main__':
    bc1 = create_barcode(0.25)
    bc2 = create_barcode(0.35)
    bc3 = create_barcode(0.375)
    print(f"Barcode widths: 0.25mm={bc1.width}, 0.35mm={bc2.width}, 0.375mm={bc3.width}")
