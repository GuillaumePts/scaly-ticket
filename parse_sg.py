import re

data = open('impression_filey.prn', 'rb').read()
matches = re.finditer(rb'\{SG;(\d{4}),(\d{4}),(\d{4}),(\d{4}),(\d),', data)
for m in matches:
    print(f"SG Command: X={m.group(1).decode()}, Y={m.group(2).decode()}, W={m.group(3).decode()}, H={m.group(4).decode()}, Mode={m.group(5).decode()}")
