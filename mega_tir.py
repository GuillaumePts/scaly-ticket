import win32print
import win32ui
import win32con
import time

def mega_tir():
    print("--- DEBUT DU MEGA-TIR ---")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    
    # Protocoles
    zpl_data = b"^XA^FO50,50^A0N,50,50^FDMEGA TIR ZPL^FS^XZ"
    tpcl_data = b"\x1bAX\x1bXS\x1bI" # Reset + Feed
    
    for (flags, description, name, comment) in printers:
        name_upper = name.upper()
        if "TEC" in name_upper or "TOSHIBA" in name_upper:
            print(f"\n>>> TEST SUR : {name}")
            
            # 1. TEST ZPL RAW
            try:
                h = win32print.OpenPrinter(name)
                print(f"  [RAW-ZPL] Envoi...")
                win32print.StartDocPrinter(h, 1, ("MegaTir ZPL", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, zpl_data)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
                win32print.ClosePrinter(h)
                print("    Succès système.")
            except Exception as e:
                print(f"    Erreur : {e}")
            
            time.sleep(0.5)

            # 2. TEST TPCL RAW
            try:
                h = win32print.OpenPrinter(name)
                print(f"  [RAW-TPCL] Envoi...")
                win32print.StartDocPrinter(h, 1, ("MegaTir TPCL", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, tpcl_data)
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
                win32print.ClosePrinter(h)
                print("    Succès système.")
            except Exception as e:
                print(f"    Erreur : {e}")

            time.sleep(0.5)

            # 3. TEST GDI (Graphique)
            try:
                print(f"  [GDI-GRAPHIC] Tentative dessin...")
                hDC = win32ui.CreateDC()
                hDC.CreatePrinterDC(name)
                hDC.StartDoc("MegaTir GDI")
                hDC.StartPage()
                # Un gros carré noir et du texte
                hDC.FillSolidRect((0, 0, 100, 100), 0)
                hDC.TextOut(110, 20, "GDI OK")
                hDC.EndPage()
                hDC.EndDoc()
                hDC.DeleteDC()
                print("    Succès système.")
            except Exception as e:
                print(f"    Erreur : {e}")

    print("\n--- MEGA-TIR TERMINE ---")

if __name__ == "__main__":
    mega_tir()
