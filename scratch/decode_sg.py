import re

def main():
    data = open('prn_file_exemple/exemplePrn.prn', 'rb').read()
    sgs = re.findall(b'\{SG;([^,]+),([^,]+),([^,]+),([^,]+),3,(.*?)\|\}', data, flags=re.DOTALL)
    
    print(f"Found {len(sgs)} SG commands")
    for i, (x, y, w, h, payload) in enumerate(sgs):
        # width in bytes
        wb = int(w) // 8
        
        # Count lines by reading cl1
        lines = 0
        idx = 0
        while idx < len(payload):
            if idx >= len(payload): break
            cl1 = payload[idx]
            idx += 1
            if cl1 > 0:
                for l1 in range(8):
                    if idx >= len(payload): break
                    if (cl1 & (1 << (7-l1))):
                        cl2 = payload[idx]
                        idx += 1
                        for l2 in range(1, 9):
                            if idx >= len(payload): break
                            if (cl2 & (1 << (8-l2))):
                                cl3 = payload[idx]
                                idx += 1
                                for l3 in range(1, 9):
                                    if idx >= len(payload): break
                                    if (cl3 & (1 << (8-l3))):
                                        idx += 1
            lines += 1
            
        print(f"SG {i}: X={x.decode()} Y={y.decode()} W={w.decode()} H={h.decode()} PayloadLen={len(payload)} -> DecodedLines={lines}")

if __name__ == '__main__':
    main()
