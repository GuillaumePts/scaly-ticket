import re, os, json

folder = 'etiquette_allemand'
labels = {}

for fname in sorted(os.listdir(folder)):
    path = os.path.join(folder, fname)
    with open(path, 'rb') as f:
        data = f.read()
    
    ascii_strings = re.findall(b'[ -~]{3,}', data)
    all_text = ' '.join(s.decode('latin-1', errors='replace') for s in ascii_strings)
    
    # Find text block between quotes starting with Franz
    idx = all_text.find('"Franz')
    if idx == -1:
        idx = all_text.find('"N/A')
        if idx == -1:
            name = os.path.splitext(fname)[0]
            labels[name] = ""
            continue
    end_idx = all_text.find('"', idx + 1)
    if end_idx == -1:
        end_idx = len(all_text)
    
    desc = all_text[idx+1:end_idx]
    desc = desc.replace('\\\\r\\\\n', '\n').replace('\\r\\n', '\n')
    desc = '\n'.join(line.rstrip() for line in desc.split('\n'))
    
    name = os.path.splitext(fname)[0]
    labels[name] = desc.strip()

with open('etiquette_allemand/labels.json', 'w', encoding='utf-8') as f:
    json.dump(labels, f, indent=2, ensure_ascii=False)

print("Done. Labels extracted:")
for k, v in labels.items():
    print(f"  {k}: {len(v)} chars")
