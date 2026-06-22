import io
import barcode
from barcode.writer import ImageWriter
from PIL import Image

data = {"gtin": "03760205241031", "date_expiration": "260618", "lot": "2103"}
barcode_data = f"01{data['gtin']}17{data['date_expiration']}10{data['lot']}"
stream = io.BytesIO()
fp = barcode.get('gs1_128', barcode_data, writer=ImageWriter())
fp.write(stream, options={
    'dpi': 203,
    'module_width': 0.35,
    'module_height': 8.0,
    'quiet_zone': 2.0,
    'write_text': False,
})
stream.seek(0)
bc_img = Image.open(stream).convert('1')
print("Barcode size:", bc_img.size)
