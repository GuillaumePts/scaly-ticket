"""
diagnostic_bev4.py
==================
Script de diagnostic pour identifier la structure TPCL acceptée par la Toshiba B-EV4.

USAGE : python diagnostic_bev4.py
Répondez au prompt pour choisir quel test envoyer.
"""

import sys
import socket
import time
import io

# ── Import du moteur de rendu (même logique que la prod) ─────────────────────
sys.path.insert(0, '.')
from PIL import Image
from src.zpl_engine import ZPLEngine

PRINTER_IP  = "200.200.129.201"  # IP de la Toshiba Gravigny (B-EV4)
PRINTER_PORT = 9100

# ─────────────────────────────────────────────────────────────────────────────
# Générateurs des différentes variantes à tester
# ─────────────────────────────────────────────────────────────────────────────

def make_test_image():
    """Image blanche 768x1200 (même taille que la prod). Servira de base pour tous les tests."""
    engine = ZPLEngine(dpi=203)
    from PIL import ImageDraw
    img = Image.new('1', (engine.TOSHIBA_CANVAS_W, engine.TOSHIBA_CANVAS_H), color=1)
    # Rectangle noir au centre pour forcer un payload SG non-vide
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 718, 1150], fill=0)
    print(f"  Image de test : {engine.TOSHIBA_CANVAS_W}x{engine.TOSHIBA_CANVAS_H} avec rectangle noir (contenu reel)")
    return img, engine

def build_variant_A(img, engine):
    """
    VARIANTE A — Identique à la B-FV4D (Saint Graal : H=0300 fictif, payload réel = 1200 lignes).
    C'est ce qu'on envoie actuellement. Va vraisemblablement échouer sur la B-EV4.
    """
    return engine._build_tpcl_job(img, quantity=1)

def build_variant_B(img, engine):
    """
    VARIANTE B — Découpage classique en vrais chunks de 300 lignes (pas de trick).
    Teste si la B-EV4 accepte les SG > 1 commandes.
    """
    img_w, img_h = img.size
    w_bytes = img_w // 8
    raw = img.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)

    header = (
        b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
    )

    sg_block = b""
    chunk_h = 300
    for y_start in range(0, img_h, chunk_h):
        y_end = min(y_start + chunk_h, img_h)
        real_h = y_end - y_start
        chunk_raw = bytearray()
        for y in range(y_start, y_end):
            row_start = y * w_bytes
            chunk_raw.extend(inv[row_start:row_start + w_bytes])
        comp = engine.compress_topix(w_bytes, real_h, bytes(chunk_raw))
        if len(comp) == 0:
            print(f"  [chunk y={y_start}] vide, ignoré.")
            continue
        sg = f"{{SG;0000,{y_start:04d},{img_w:04d},{real_h:04d},3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        sg_block += sg

    footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    return header + sg_block + footer

def build_variant_C(img, engine):
    """
    VARIANTE C — Saint Graal MAIS avec H = hauteur réelle de l'image (pas 0300).
    Teste si la B-EV4 accepte H > 300 dans la commande SG.
    """
    img_w, img_h = img.size
    w_bytes = img_w // 8
    raw = img.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)

    header = (
        b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
    )
    comp = engine.compress_topix(w_bytes, img_h, inv)
    # H = hauteur réelle (1200)
    sg = f"{{SG;0000,0000,{img_w:04d},{img_h:04d},3,".encode('ascii')
    clen = len(comp)
    sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"

    footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    return header + sg + footer

def build_variant_D(img, engine):
    """
    VARIANTE D — Chunks de 300 MAIS avec un footer XS différent (sans le code 0002C5000).
    Teste si le code de coupe/avance est différent sur la B-EV4.
    """
    img_w, img_h = img.size
    w_bytes = img_w // 8
    raw = img.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)

    header = (
        b"<xpml><page quantity='0' pitch='120.1 mm'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1' pitch='120.1 mm'></xpml>{C|}\r\n"
    )

    sg_block = b""
    chunk_h = 300
    for y_start in range(0, img_h, chunk_h):
        y_end = min(y_start + chunk_h, img_h)
        real_h = y_end - y_start
        chunk_raw = bytearray()
        for y in range(y_start, y_end):
            row_start = y * w_bytes
            chunk_raw.extend(inv[row_start:row_start + w_bytes])
        comp = engine.compress_topix(w_bytes, real_h, bytes(chunk_raw))
        if len(comp) == 0:
            continue
        sg = f"{{SG;0000,{y_start:04d},{img_w:04d},{real_h:04d},3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        sg_block += sg

    # Footer simplifié sans code spécial
    footer = b"{XS;I,0001,|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    return header + sg_block + footer

def build_variant_E(img, engine):
    """
    VARIANTE E — XPML sans attribut pitch dans les balises sentinelles.
    Certains firmwares B-EV4 n'acceptent pas l'attribut pitch dans la balise page.
    """
    img_w, img_h = img.size
    w_bytes = img_w // 8
    raw = img.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)

    # Balises sentinelles SANS attribut pitch
    header = (
        b"<xpml><page quantity='0'></xpml>{D1221,0975,1201|}\r\n"
        b"<xpml></page></xpml><xpml><page quantity='1'></xpml>{C|}\r\n"
    )
    comp = engine.compress_topix(w_bytes, img_h, inv)
    sg = f"{{SG;0000,0000,{img_w:04d},0300,3,".encode('ascii')
    clen = len(comp)
    sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"

    footer = b"{XS;I,0001,0002C5000|}\r\n<xpml></page></xpml><xpml><end/></xpml>\r\n"
    return header + sg + footer

def build_variant_F(img, engine):
    """
    VARIANTE F — Chunks TPCL pur SANS balises XPML sentinelles.
    Teste si la B-EV4 utilise un TPCL pur sans encapsulation XPML.
    """
    img_w, img_h = img.size
    w_bytes = img_w // 8
    raw = img.tobytes()
    inv = bytes(b ^ 0xFF for b in raw)

    # Header TPCL pur, sans XPML
    header = b"{D1221,0975,1201|}\r\n{C|}\r\n"

    sg_block = b""
    chunk_h = 300
    for y_start in range(0, img_h, chunk_h):
        y_end = min(y_start + chunk_h, img_h)
        real_h = y_end - y_start
        chunk_raw = bytearray()
        for y in range(y_start, y_end):
            row_start = y * w_bytes
            chunk_raw.extend(inv[row_start:row_start + w_bytes])
        comp = engine.compress_topix(w_bytes, real_h, bytes(chunk_raw))
        if len(comp) == 0:
            continue
        sg = f"{{SG;0000,{y_start:04d},{img_w:04d},{real_h:04d},3,".encode('ascii')
        clen = len(comp)
        sg += bytes([clen >> 8, clen & 0xFF]) + comp + b"|}\r\n"
        sg_block += sg

    footer = b"{XS;I,0001,0002C5000|}\r\n"
    return header + sg_block + footer

# ─────────────────────────────────────────────────────────────────────────────
# Envoi TCP (identique au PrinterClient de prod)
# ─────────────────────────────────────────────────────────────────────────────

def send_to_printer(payload: bytes, ip: str = PRINTER_IP, port: int = PRINTER_PORT):
    print(f"\n  Connexion a {ip}:{port}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10.0)
            s.connect((ip, port))
            s.sendall(payload)
            print(f"  OK - {len(payload)} octets envoyes.")
            s.shutdown(socket.SHUT_WR)
            print("  Attente 2.0s (flush TCP Toshiba)...")
            time.sleep(2.0)
        print("  Socket ferme proprement.")
    except Exception as e:
        print(f"  ERREUR reseau : {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

VARIANTS = {
    'A': ("B-FV4D prod (Saint Graal H=0300)",          build_variant_A),
    'B': ("Chunks reels 300 lignes + footer prod",      build_variant_B),
    'C': ("Saint Graal H=HAUTEUR_REELLE (1200)",        build_variant_C),
    'D': ("Chunks reels 300 lignes + footer simplifie", build_variant_D),
    'E': ("Saint Graal sans pitch dans balises XPML",   build_variant_E),
    'F': ("Chunks TPCL pur SANS balises XPML",          build_variant_F),
}

if __name__ == "__main__":
    print("=" * 60)
    print(" DIAGNOSTIC TPCL - Toshiba B-EV4 Gravigny")
    print("=" * 60)
    print(f" Cible : {PRINTER_IP}:{PRINTER_PORT}\n")
    print(" Variantes disponibles :")
    for k, (desc, _) in VARIANTS.items():
        print(f"   [{k}] {desc}")
    print()

    choice = input(" Entrez la lettre de la variante a tester (ex: B) : ").strip().upper()

    if choice not in VARIANTS:
        print(f"Variante '{choice}' inconnue. Sortie.")
        sys.exit(1)

    desc, builder = VARIANTS[choice]
    print(f"\n--- Test [{choice}] : {desc} ---")

    img, engine = make_test_image()
    payload = builder(img, engine)
    print(f"  Taille du payload : {len(payload)} octets")

    send_to_printer(payload)

    print("\n  Observez la reaction de l'imprimante :")
    print("  OK  - Impression (meme blanche) = structure acceptee !")
    print("  NOK - Voyant rouge              = structure refusee, essayez une autre variante.")
    print()
