import csv
import logging
import io
import shutil
import sys
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from src.config import settings, base_path
from src.models import TicketData
from src.zpl_engine import ZPLEngine
from src.printer import PrinterClient
from src.utils import get_days_offset, get_updated_dlc, get_updated_lot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scaly-Ticket API")

# Setup templates and static files
static_dir = str(base_path / "static")
templates_dir = str(base_path / "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

from fastapi.responses import HTMLResponse, FileResponse

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"printers": settings.printers}
    )

# Flag global d'annulation
is_cancelled = False

@app.post("/stop-print")
async def stop_print():
    global is_cancelled
    is_cancelled = True
    return {"message": "Demande d'arrêt envoyée."}

class PrintJobRequest(BaseModel):
    printer_ip: str
    printer_dpi: int
    printer_language: str = "ZPL"
    offset_x: int = 800
    offset_y: int = 18
    title_size: int = 0
    title_bold: bool = False
    gs1_size: int = 0
    gs1_bold: bool = False
    lot_size: int = 0
    lot_bold: bool = False
    items: List[TicketData]

class PrintNatureRequest(BaseModel):
    printer_ip: str
    printer_dpi: int
    printer_language: str = "TPCL"
    quantity: int

class Print4UpRequest(BaseModel):
    printer_ip: str
    printer_dpi: int
    printer_language: str = "TPCL"
    parfum_id: str
    quantity: int
    offset_x: int = 0
    offset_y: int = 0
    title_size: int = 0
    title_bold: bool = False
    gs1_size: int = 0
    gs1_bold: bool = False
    lot_size: int = 0
    lot_bold: bool = False

@app.post("/print-nature")
async def print_nature(request: PrintNatureRequest):
    global is_cancelled
    is_cancelled = False
    
    try:
        engine = ZPLEngine(dpi=request.printer_dpi)
        printer = PrinterClient(host=request.printer_ip)
        
        if request.printer_language == "TPCL":
            flux = engine.generate_4up_nature_tpcl(request.quantity)
        else:
            flux = engine.generate_4up_nature_zpl(request.quantity)
        
        printer.send_zpl(flux)
        return {"message": f"Impression réseau ({request.printer_language}) envoyée."}

    except Exception as e:
        logger.error(f"Erreur impression Nature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/parfums-4up")
async def get_parfums_4up():
    try:
        path = base_path / "data" / "parfums_4up.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement parfums: {e}")
        return []

class Parfum4Up(BaseModel):
    nom: str
    ean13: str

@app.post("/api/parfums-4up")
async def add_parfum_4up(parfum: Parfum4Up):
    try:
        path = base_path / "data" / "parfums_4up.json"
        with open(path, "r", encoding="utf-8") as f:
            parfums = json.load(f)
            
        import uuid
        new_id = str(uuid.uuid4())
        new_parfum = {
            "id": new_id,
            "nom": parfum.nom,
            "ean13": parfum.ean13
        }
        parfums.append(new_parfum)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(parfums, f, indent=4, ensure_ascii=False)
            
        return {"message": "Parfum ajouté", "parfum": new_parfum}
    except Exception as e:
        logger.error(f"Erreur ajout parfum: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-4up-live")
async def preview_4up_live(nom: str, ean13: str):
    try:
        engine = ZPLEngine(dpi=203)
        parfum = {"nom": nom, "ean13": ean13}
        img_bytes = engine.generate_4up_preview_png(parfum)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview 4-up live: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-4up/{parfum_id}")
async def preview_4up(parfum_id: str):
    try:
        path = base_path / "data" / "parfums_4up.json"
        with open(path, "r", encoding="utf-8") as f:
            parfums = json.load(f)
            
        parfum = next((p for p in parfums if p["id"] == parfum_id), None)
        if not parfum:
            raise HTTPException(status_code=404, detail="Parfum non trouvé")
            
        engine = ZPLEngine(dpi=203)
        img_bytes = engine.generate_4up_preview_png(parfum)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview 4-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/print-4up")
async def print_4up(request: Print4UpRequest):
    global is_cancelled
    is_cancelled = False
    
    try:
        path = base_path / "data" / "parfums_4up.json"
        with open(path, "r", encoding="utf-8") as f:
            parfums = json.load(f)
            
        parfum = next((p for p in parfums if p["id"] == request.parfum_id), None)
        if not parfum:
            raise HTTPException(status_code=404, detail="Parfum non trouvé")
            
        engine = ZPLEngine(dpi=request.printer_dpi)
        printer = PrinterClient(host=request.printer_ip)

        # Même détection que /print-json : B-EV4 Gravigny sans pitch dans XPML
        printer_info = next((p for p in settings.printers if p.get("ip") == request.printer_ip), {})
        xpml_pitch = printer_info.get("sector", "") != "Gravigny"

        if request.printer_language == "TPCL":
            styling = {
                "title_size": request.title_size, "title_bold": request.title_bold,
                "gs1_size": request.gs1_size, "gs1_bold": request.gs1_bold,
                "lot_size": request.lot_size, "lot_bold": request.lot_bold
            }
            flux = engine.generate_4up_toshiba_tpcl(parfum, request.quantity, offset_x=request.offset_x, offset_y=request.offset_y, styling=styling, xpml_pitch=xpml_pitch)
        else:
            # Fallback ou autre imprimante, non implémenté pour l'instant
            raise HTTPException(status_code=400, detail="ZPL non supporté pour ce format")
            
        printer.send_zpl(flux)
        return {"message": f"Impression 4-up de {request.quantity} étiquettes envoyée."}

    except Exception as e:
        logger.error(f"Erreur impression 4-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/print-json")
async def print_json(request: PrintJobRequest):
    global is_cancelled
    is_cancelled = False
    engine = ZPLEngine(dpi=request.printer_dpi)
    printer = PrinterClient(host=request.printer_ip)
    lang = request.printer_language

    # Détecter si l'imprimante est sur le secteur Gravigny (B-EV4) :
    # La B-EV4 rejette l'attribut pitch='120.1 mm' dans les balises sentinelles XPML.
    # (Validé par diagnostic juillet 2026 : variante E = OK, variante A avec pitch = voyant rouge)
    printer_info = next((p for p in settings.printers if p.get("ip") == request.printer_ip), {})
    xpml_pitch = printer_info.get("sector", "") != "Gravigny"

    try:
        first_job = True
        full_flux = ""
        for ticket in request.items:
            if is_cancelled:
                return {"message": "Impression annulée."}
            
            # Plus besoin de printer.wait_until_ready() à chaque étiquette, 
            # la machine va buffuriser le gros flux réseau d'un coup.
            if not first_job:
                if lang == "TPCL":
                    sep = engine.generate_separator_tpcl(ticket.libelle, xpml_pitch=xpml_pitch)
                    full_flux += sep
            
            first_job = False
            
            days_offset = get_days_offset(ticket.date_expiration)
            
            # Gestion du format : 3-up (TPCL) ou 1-up (ZPL Zebra)
            if lang == "TPCL":
                nb_rows = (ticket.quantite + 2) // 3
            else:
                nb_rows = ticket.quantite
                
            if is_cancelled:
                return {"message": "Impression interrompue."}
                
            styling = {
                "title_size": request.title_size, "title_bold": request.title_bold,
                "gs1_size": request.gs1_size, "gs1_bold": request.gs1_bold,
                "lot_size": request.lot_size, "lot_bold": request.lot_bold
            }
                
            if lang == "TPCL":
                # On génère l'image UNE SEULE FOIS pour le groupe avec la quantité matérielle
                flux = engine.generate_ticket_tpcl(ticket, quantity=nb_rows, offset_x=request.offset_x, offset_y=request.offset_y, styling=styling, xpml_pitch=xpml_pitch)
                full_flux += flux
            else:
                # Pour Zebra (ZPL), le texte est léger, on peut concaténer
                for _ in range(nb_rows):
                    flux = engine.generate_ticket_zebra_300(ticket, offset_x=request.offset_x, offset_y=request.offset_y, styling=styling)
                    full_flux += flux
                    
        # Envoi d'un seul énorme bloc pour éviter la lenteur réseau et les temps morts
        if full_flux:
            printer.send_zpl(full_flux)
            
        return {"message": f"Impression de {len(request.items)} produits terminée en rafale."}

    except Exception as e:
        logger.error(f"Erreur impression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/printer-status")
async def get_printer_status(ip: str):
    printer = PrinterClient(host=ip)
    status = printer.get_status()
    if "error" in status:
        return {"error": status["error"], "ready": False}
    
    ready = not (status.get("paper_out") or status.get("pause") or 
                 status.get("ribbon_out") or status.get("head_open"))
    return {"ready": ready, "details": status}

@app.get("/api/printers")
async def get_printers():
    return settings.printers

@app.post("/api/printers")
async def save_printers(printers: List[dict]):
    exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(os.getcwd())
    path = exe_dir / settings.PRINTERS_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(printers, f, indent=4)
    return {"message": "Configuration sauvegardée."}

@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    printer_ip: str = Form(...),
    printer_dpi: int = Form(...),
    printer_language: str = Form("ZPL")
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptés.")

    content = await file.read()
    decoded = content.decode('utf-8')
    f = io.StringIO(decoded)
    reader = csv.DictReader(f, delimiter=";")

    engine = ZPLEngine(dpi=printer_dpi)
    printer = PrinterClient(host=printer_ip)
    lang = printer_language

    try:
        first_job = True
        full_flux = ""
        for row in reader:
            ticket = TicketData(**row)

            if not first_job:
                if lang == "TPCL":
                    sep = engine.generate_separator_tpcl(ticket.libelle)
                    full_flux += sep
            
            first_job = False
            
            days_offset = get_days_offset(ticket.date_expiration)
            
            # Gestion du format : 3-up (TPCL) ou 1-up (ZPL Zebra)
            if lang == "TPCL":
                nb_rows = (ticket.quantite + 2) // 3
            else:
                nb_rows = ticket.quantite
                
            current_dlc = ticket.date_expiration

            for i in range(nb_rows):
                if is_cancelled:
                    return {"message": "Impression interrompue."}
                
                new_dlc = get_updated_dlc(days_offset)
                if new_dlc != current_dlc:
                    new_lot = get_updated_lot(ticket.lot)
                    current_dlc = new_dlc
                    ticket.date_expiration = new_dlc
                    ticket.lot = new_lot
                    ticket.num_lot_display = new_lot
                
                if lang == "TPCL":
                    flux = engine.generate_ticket_tpcl(ticket)
                else:
                    flux = engine.generate_ticket_zebra_300(ticket, offset_x=offset_x, offset_y=offset_y)
                    
                full_flux += flux
        
        if full_flux:
            printer.send_zpl(full_flux)
            
        return {"message": f"Impression réseau lancée pour {file.filename}."}

    except Exception as e:
        logger.error(f"Erreur upload CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-zebra-1up")
async def preview_zebra_1up(
    title_size: int = 0, title_bold: str = "false",
    gs1_size: int = 0, gs1_bold: str = "false",
    lot_size: int = 0, lot_bold: str = "false"
):
    try:
        engine = ZPLEngine(dpi=300)
        ticket = TicketData(
            libelle="YAOURT NATURE", 
            gtin="12345678901234", 
            date_expiration="240831", 
            lot="L123", 
            quantite=1,
            Client="TEST",
            Commande="CMD-TEST",
            DateLivraison="01/01/2026",
            Numlot="L123"
        )
        styling = {
            "title_size": title_size, "title_bold": title_bold == "true",
            "gs1_size": gs1_size, "gs1_bold": gs1_bold == "true",
            "lot_size": lot_size, "lot_bold": lot_bold == "true"
        }
        img_bytes = engine.generate_zebra_1up_preview_png(ticket, styling)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview Zebra: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-3up")
async def preview_3up(
    title_size: int = 0, title_bold: str = "false",
    gs1_size: int = 0, gs1_bold: str = "false",
    lot_size: int = 0, lot_bold: str = "false"
):
    try:
        # Dummy data for preview
        dummy_ticket = TicketData(
            libelle="6 Yaourt entier Fraise",
            gtin="03412345678901",
            date_expiration="260630",
            lot="L123456",
            Numlot="Lot: L123456 - DLC: 30/06/2026",
            Client="FERME",
            Commande="CMD-PREVIEW",
            DateLivraison="30/06/2026",
            Quantite=1
        )
        engine = ZPLEngine(dpi=203)
        styling = {
            "title_size": title_size, "title_bold": title_bold == "true",
            "gs1_size": gs1_size, "gs1_bold": gs1_bold == "true",
            "lot_size": lot_size, "lot_bold": lot_bold == "true"
        }
        img_bytes = engine.generate_3up_band_preview_png(dummy_ticket, styling)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview 3-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-4up-demo")
async def get_preview_4up_demo(
    title_size: int = 0, title_bold: str = "false",
    gs1_size: int = 0, gs1_bold: str = "false",
    lot_size: int = 0, lot_bold: str = "false"
):
    try:
        engine = ZPLEngine(dpi=203)
        parfum = {"nom": "Yaourt Fraise", "ean13": "3412345678918"}
        styling = {
            "title_size": title_size, "title_bold": title_bold == "true",
            "gs1_size": gs1_size, "gs1_bold": gs1_bold == "true",
            "lot_size": lot_size, "lot_bold": lot_bold == "true"
        }
        img_bytes = engine.generate_4up_band_preview_png(parfum, styling)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview 4-up demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preview-zebra-2up")
async def get_preview_zebra_2up(
    title_size: int = 0, title_bold: str = "false",
    gs1_size: int = 0, gs1_bold: str = "false",
    lot_size: int = 0, lot_bold: str = "false"
):
    try:
        engine = ZPLEngine(dpi=203)
        parfum = {"nom": "Yaourt Fraise", "ean13": "3412345678918"}
        styling = {
            "title_size": title_size, "title_bold": title_bold == "true",
            "gs1_size": gs1_size, "gs1_bold": gs1_bold == "true",
            "lot_size": lot_size, "lot_bold": lot_bold == "true"
        }
        img_bytes = engine.generate_zebra_2up_preview_png(parfum, styling)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview zebra 2-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class PrinterOffsetsRequest(BaseModel):
    ip: str
    offset_x: int
    offset_y: int
    title_size: int = 0
    title_bold: bool = False
    gs1_size: int = 0
    gs1_bold: bool = False
    lot_size: int = 0
    lot_bold: bool = False

@app.post("/api/update-printer-offsets")
async def update_printer_offsets(req: PrinterOffsetsRequest):
    path = base_path / settings.PRINTERS_FILE
    if not path.exists():
        raise HTTPException(status_code=404, detail="printers.json introuvable")
    
    with open(path, "r", encoding="utf-8") as f:
        printers = json.load(f)
        
    updated = False
    for p in printers:
        if p.get("ip") == req.ip:
            p["offset_x"] = req.offset_x
            p["offset_y"] = req.offset_y
            
            p["title_size"] = req.title_size
            p["title_bold"] = req.title_bold
            p["gs1_size"] = req.gs1_size
            p["gs1_bold"] = req.gs1_bold
            p["lot_size"] = req.lot_size
            p["lot_bold"] = req.lot_bold
            
            updated = True
            break
            
    if updated:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(printers, f, indent=4)
        # Met à jour le cache en mémoire (optionnel)
        settings.printers.clear()
        settings.printers.extend(printers)
        return {"message": "Offsets sauvegardés"}
    else:
        raise HTTPException(status_code=404, detail="Imprimante non trouvée")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
