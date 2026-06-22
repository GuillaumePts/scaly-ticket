import re

with open('prn_file_exemple/exemplePrn.prn', 'rb') as f:
    data = f.read()

print("--- DEBUT DU FICHIER ---")
print(data[:500].decode('ascii', errors='ignore'))

print("\n--- COMMANDES SG (GRAPHIQUES) ---")
matches = re.finditer(rb'\{SG;(\d{4}),(\d{4}),(\d{4}),(\d{4}),(\d),', data)
for m in matches:
    start_idx = m.end()
    length = data[start_idx] * 256 + data[start_idx+1]
    print(f"SG Command: X={m.group(1).decode()}, Y={m.group(2).decode()}, W={m.group(3).decode()}, H={m.group(4).decode()}, PayloadLen={length}")

print("\n--- FIN DU FICHIER ---")
print(data[-200:].decode('ascii', errors='ignore'))
