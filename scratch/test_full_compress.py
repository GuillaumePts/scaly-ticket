import sys
sys.path.append('.')
from src.zpl_engine import ZPLEngine
from PIL import Image, ImageDraw, ImageFont

img = Image.new('1', (800, 300), color=1)
draw = ImageDraw.Draw(img)
try: font = ImageFont.truetype("arial.ttf", 36)
except: font = ImageFont.load_default()
draw.text((10, 10), "6 Yaourts entier Abricot Vanille RGF", fill=0, font=font)

raw = img.tobytes()
inv = bytes(b ^ 0xFF for b in raw)
engine = ZPLEngine(203)
comp = engine.compress_topix(100, 300, inv)
print(f"Compressed size for 300 dots: {len(comp)} bytes")
