import sys, socket, io
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from test_toshiba_layout_fix import compress_topix, DATA

# 20mm = 160 dots, 80mm = 640 dots
W_DOTS = 160
H_DOTS = 640

def render_label(data):
    # Landscape 640x160
    img_w, img_h = 640, 160
    image = Image.new('1', (img_w, img_h), color=1)
    draw = ImageDraw.Draw(image)
    try: font = ImageFont.truetype("arialbd.ttf", 20)
    except: font = ImageFont.load_default()
    draw.text((10, 10), data["libelle"], fill=0, font=font)
    return image.transpose(Image.ROTATE_90)

def build_job(image):
    raw = image.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)
    img_w, img_h = image.size
    comp = compress_topix(img_w // 8, img_h, inv)
    
    header = (
        b"<xpml><page quantity='0' pitch='115.0 mm'></xpml>\r\n"
        b"{D1150,1016,1150|}\r\n"
        b"<xpml></page></xpml>\r\n"
        b"<xpml><page quantity='1' pitch='115.0 mm'></xpml>\r\n"
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
        print("Envoye V4 (20x80 pur)")
