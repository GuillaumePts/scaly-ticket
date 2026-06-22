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
        
        if request.printer_language == "TPCL":
            flux = engine.generate_4up_toshiba_tpcl(parfum, request.quantity)
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

    try:
        first_job = True
        full_flux = ""
        for ticket in request.items:
            if is_cancelled:
                return {"message": "Impression annulée."}
            
            # Plus besoin de printer.wait_until_ready() à chaque étiquette, 
            # la machine va buffuriser le gros flux réseau d'un coup.
            if not first_job:
                sep = engine.generate_separator_tpcl(ticket.libelle) if lang == "TPCL" else engine.generate_separator_zpl(ticket.libelle)
                full_flux += sep
            
            first_job = False
            
            days_offset = get_days_offset(ticket.date_expiration)
            nb_rows = (ticket.quantite + 2) // 3
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
                
                flux = engine.generate_ticket_tpcl(ticket) if lang == "TPCL" else engine.generate_ticket_zpl(ticket)
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
                sep = engine.generate_separator_tpcl(ticket.libelle) if lang == "TPCL" else engine.generate_separator_zpl(ticket.libelle)
                full_flux += sep
            
            first_job = False
            
            days_offset = get_days_offset(ticket.date_expiration)
            nb_rows = (ticket.quantite + 2) // 3
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
                
                flux = engine.generate_ticket_tpcl(ticket) if lang == "TPCL" else engine.generate_ticket_zpl(ticket)
                full_flux += flux
        
        if full_flux:
            printer.send_zpl(full_flux)
            
        return {"message": f"Impression de {file.filename} terminée en rafale."}

    except Exception as e:
        logger.error(f"Erreur impression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
