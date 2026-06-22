from PIL import Image

def find_empty_rows(img):
    w, h = img.size
    empty = []
    
    # Fast row check
    raw = img.tobytes()
    width_bytes = w // 8
    
    for y in range(h):
        line_start = y * width_bytes
        # In '1' mode, white is 0xFF, but inverted in our code it is 0.
        # But here img is not inverted yet. So white is 0xFF.
        if all(raw[i] == 255 for i in range(line_start, line_start + width_bytes)):
            empty.append(y)
    return empty

img = Image.new('1', (800, 1200), color=1)
from PIL import ImageDraw, ImageFont
draw = ImageDraw.Draw(img)
# Draw some text
try:
    font = ImageFont.truetype("arial.ttf", 36)
except:
    font = ImageFont.load_default()
    
draw.text((10, 10), "6 Yaourt", fill=0, font=font)
draw.text((10, 300), "entier", fill=0, font=font)
draw.text((10, 590), "Abricot", fill=0, font=font)

empty_rows = find_empty_rows(img)
print(f"Total empty rows: {len(empty_rows)}")

def get_chunks(img_h, empty_rows, max_h=300):
    chunks = []
    y = 0
    empty_set = set(empty_rows)
    while y < img_h:
        if y + max_h >= img_h:
            chunks.append((y, img_h - y))
            break
        
        split_y = y + max_h
        # find the nearest empty row looking backwards
        found = False
        for s in range(split_y, y, -1):
            if s in empty_set:
                split_y = s
                found = True
                break
        
        if not found:
            # fallback to hard split
            split_y = y + max_h
            
        chunks.append((y, split_y - y))
        y = split_y
    return chunks

print(get_chunks(1200, empty_rows))
