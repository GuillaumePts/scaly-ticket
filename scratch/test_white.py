import sys
sys.path.append('.')
from src.zpl_engine import ZPLEngine
engine = ZPLEngine(203)
inv = bytearray([0x00] * (100 * 300))
comp = engine.compress_topix(100, 300, inv)
print(f"White chunk compressed size: {len(comp)}")
