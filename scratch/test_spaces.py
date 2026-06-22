from PIL import Image, ImageDraw, ImageFont
img = Image.new('1', (800, 1200), color=1)
draw = ImageDraw.Draw(img)
try: font = ImageFont.truetype("arial.ttf", 36)
except: font = ImageFont.load_default()
draw.text((10, 10), "Yaourt entier", fill=0, font=font)
img = img.transpose(Image.ROTATE_90)
raw = img.tobytes()
empty_rows = set()
for y in range(800):
    start = y * 150
    if all(raw[i] == 255 for i in range(start, start + 150)):
        empty_rows.add(y)
print(f"Empty rows found: {len(empty_rows)}")
