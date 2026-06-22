import re

def parse_sg(data):
    # Find all SG commands
    pattern = b'\{SG;(\d{4}),(\d{4}),(\d{4}),(\d{4}),(\d),'
    matches = list(re.finditer(pattern, data))
    
    print(f"Found {len(matches)} SG commands.")
    
    for i, m in enumerate(matches):
        x = int(m.group(1))
        y = int(m.group(2))
        w = int(m.group(3))
        h = int(m.group(4))
        mode = int(m.group(5))
        
        start = m.end()
        # the next two bytes are the payload length
        payload_len = (data[start] << 8) | data[start+1]
        
        print(f"SG {i}: X={x:04d} Y={y:04d} W={w:04d} H={h:04d} Mode={mode} PayloadLen={payload_len}")

with open("prn_file_exemple/exemplePrn.prn", "rb") as f:
    parse_sg(f.read())
