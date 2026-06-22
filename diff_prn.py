import re

with open('test32.prn', 'rb') as f:
    d1 = f.read()
with open('prn_file_exemple/exemplePrn.prn', 'rb') as f:
    d2 = f.read()

def parse_prn(data):
    matches = list(re.finditer(rb'\{SG;(\d{4}),(\d{4}),(\d{4}),(\d{4}),(\d),', data))
    headers = data[:matches[0].start()] if matches else b''
    
    footers_start = matches[-1].end() if matches else 0
    if matches:
        last_m = matches[-1]
        start_idx = last_m.end()
        length = data[start_idx] * 256 + data[start_idx+1]
        footers_start = start_idx + 2 + length + 4 # 4 is |}\r\n
    
    footers = data[footers_start:] if matches else data
    
    sgs = []
    for m in matches:
        start_idx = m.end()
        length = data[start_idx] * 256 + data[start_idx+1]
        sgs.append({
            'X': m.group(1).decode(),
            'Y': m.group(2).decode(),
            'W': m.group(3).decode(),
            'H': m.group(4).decode(),
            'Len': length
        })
    return headers, sgs, footers

h1, s1, f1 = parse_prn(d1)
h2, s2, f2 = parse_prn(d2)

print("--- HEADERS ---")
print("TEST32: ", h1)
print("EXEMPLE:", h2)
print("\n--- SGs ---")
print("TEST32: ", [(s['Y'], s['W'], s['H'], s['Len']) for s in s1])
print("EXEMPLE:", [(s['Y'], s['W'], s['H'], s['Len']) for s in s2])
print("\n--- FOOTERS ---")
print("TEST32: ", f1)
print("EXEMPLE:", f2)

