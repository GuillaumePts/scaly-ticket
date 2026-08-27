import csv
import logging
import io
import shutil
import sys
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Response, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from src.config import settings, base_path, data_path, db
from src.models import TicketData
from src.zpl_engine import ZPLEngine
from src.printer import PrinterClient
from src.utils import get_days_offset, get_updated_dlc, get_updated_lot
from src.licence import check_licence, get_licence_status, LicenceError
from src.paletisation_engine import generer_plan_palettisation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scaly-Ticket API")

# Setup templates and static files
static_dir = str(base_path / "static")
templates_dir = str(base_path / "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

from fastapi.responses import HTMLResponse, FileResponse

# --- WEBSOCKET & SPOOLER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

ws_manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@dataclass
class PrintJob:
    printer_ip: str
    printer_dpi: int
    lang: str
    flux: str
    sleep_time: float

print_queues: Dict[str, asyncio.Queue] = {}

async def spooler_worker(ip: str):
    queue = print_queues[ip]
    while True:
        job: PrintJob = await queue.get()
        printer = PrinterClient(host=ip)
        try:
            if job.lang == "ZPL":
                # Vérification de statut Zebra (Ping & Erreurs matérielles)
                while True:
                    status = await asyncio.to_thread(printer.get_status)
                    if "error" in status:
                        await ws_manager.broadcast({"type": "status", "ip": ip, "level": "error", "message": f"Zebra injoignable ({status['error']}). Nouvel essai dans 5s..."})
                        await asyncio.sleep(5)
                        continue
                    if status.get("paper_out"):
                        await ws_manager.broadcast({"type": "status", "ip": ip, "level": "error", "message": "Zebra : Plus de papier ! En attente..."})
                        await asyncio.sleep(5)
                        continue
                    if status.get("head_open"):
                        await ws_manager.broadcast({"type": "status", "ip": ip, "level": "error", "message": "Zebra : Capot ouvert ! En attente..."})
                        await asyncio.sleep(5)
                        continue
                    if status.get("pause"):
                        await ws_manager.broadcast({"type": "status", "ip": ip, "level": "warning", "message": "Zebra en pause..."})
                        await asyncio.sleep(5)
                        continue
                    
                    await ws_manager.broadcast({"type": "status", "ip": ip, "level": "success", "message": "Zebra prête, envoi du job..."})
                    break
            else:
                # Toshiba : Juste un ping réseau (fire & forget avec fallback erreur)
                await ws_manager.broadcast({"type": "status", "ip": ip, "level": "success", "message": "Envoi vers Toshiba en cours..."})
            
            await asyncio.to_thread(printer.send_zpl, job.flux, job.sleep_time)
            await ws_manager.broadcast({"type": "status", "ip": ip, "level": "success", "message": "Job envoyé avec succès !"})
            
        except Exception as e:
            await ws_manager.broadcast({"type": "status", "ip": ip, "level": "error", "message": f"Échec fatal de l'envoi: {e}"})
        finally:
            queue.task_done()


def enqueue_job(ip: str, dpi: int, lang: str, flux: str, sleep_time: float = 2.0):
    if ip not in print_queues:
        print_queues[ip] = asyncio.Queue()
        asyncio.create_task(spooler_worker(ip))
    print_queues[ip].put_nowait(PrintJob(ip, dpi, lang, flux, sleep_time))
# ---------------------------

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"printers": db.get_printers()}
    )


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

class Print4UpItem(BaseModel):
    parfum_id: str
    quantity: int

class Print4UpRequest(BaseModel):
    printer_ip: str
    printer_dpi: int
    printer_language: str = "TPCL"
    # Nouveau : liste d'items (plusieurs parfums en un seul job)
    items: List[Print4UpItem] = []
    # Ancien format (compat) : un seul parfum
    parfum_id: str = ""
    quantity: int = 0
    offset_x: int = 0
    offset_y: int = 0
    title_size: int = 0
    title_bold: bool = False
    gs1_size: int = 0
    gs1_bold: bool = False
    lot_size: int = 0
    lot_bold: bool = False

class PalettisationRequest(BaseModel):
    items: List[dict] # [{"libelle": "...", "quantite": 100}]
    optimisation_max: bool = False
    client: str = ""

@app.post("/api/palettisation")
async def api_palettisation(request: PalettisationRequest):
    try:
        tours = generer_plan_palettisation(request.items, opt_max=request.optimisation_max, client=request.client)
        return {"success": True, "tours": tours}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/print-nature")
async def print_nature(request: PrintNatureRequest):
    global is_cancelled
    is_cancelled = False
    
    try:
        check_licence()
    except LicenceError as e:
        raise HTTPException(status_code=403, detail=str(e))
        
    try:
        engine = ZPLEngine(dpi=request.printer_dpi)
        printer = PrinterClient(host=request.printer_ip)
        
        if request.printer_language == "TPCL":
            flux = engine.generate_4up_nature_tpcl(request.quantity)
        else:
            flux = engine.generate_4up_nature_zpl(request.quantity)
        
        enqueue_job(request.printer_ip, request.printer_dpi, request.printer_language, flux, 2.0)
        return {"message": f"Impression réseau ({request.printer_language}) ajoutée à la file d'attente."}

    except Exception as e:
        logger.error(f"Erreur impression Nature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/parfums-4up")
async def get_parfums_4up():
    try:
        return db.get_parfums()
    except Exception as e:
        logger.error(f"Erreur chargement parfums: {e}")
        return []

class Parfum4Up(BaseModel):
    nom: str
    ean13: str
    nom_impression: str = None

@app.post("/api/parfums-4up")
async def add_parfum_4up(parfum: Parfum4Up):
    try:
        new_parfum = db.add_parfum(parfum.nom, parfum.ean13, parfum.nom_impression)
        return {"message": "Parfum ajouté", "parfum": new_parfum}
    except Exception as e:
        logger.error(f"Erreur ajout parfum: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/parfums-4up/{parfum_id}")
async def update_parfum_4up(parfum_id: str, parfum: Parfum4Up):
    try:
        success = db.update_parfum(parfum_id, parfum.nom, parfum.ean13, parfum.nom_impression)
        if success:
            return {"message": "Parfum mis à jour"}
        raise HTTPException(status_code=404, detail="Parfum non trouvé")
    except Exception as e:
        logger.error(f"Erreur mise à jour parfum: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/parfums-4up/{parfum_id}")
async def delete_parfum_4up(parfum_id: str):
    try:
        success = db.delete_parfum(parfum_id)
        if success:
            return {"message": "Parfum supprimé"}
        raise HTTPException(status_code=404, detail="Parfum non trouvé")
    except Exception as e:
        logger.error(f"Erreur suppression parfum: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- CRUD Parfums 3-up ---
@app.get("/api/parfums-3up")
async def get_parfums_3up_api():
    try:
        return db.get_parfums_3up()
    except Exception as e:
        logger.error(f"Erreur chargement parfums 3up: {e}")
        return []

class Parfum3Up(BaseModel):
    nom: str
    ean13: str
    nom_impression: str

@app.post("/api/parfums-3up")
async def add_parfum_3up_api(parfum: Parfum3Up):
    try:
        new_parfum = db.add_parfum_3up(parfum.nom, parfum.ean13, parfum.nom_impression)
        return {"message": "Produit ajouté", "parfum": new_parfum}
    except Exception as e:
        logger.error(f"Erreur ajout produit 3up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/parfums-3up/{parfum_id}")
async def update_parfum_3up_api(parfum_id: str, parfum: Parfum3Up):
    try:
        success = db.update_parfum_3up(parfum_id, parfum.nom, parfum.ean13, parfum.nom_impression)
        if success:
            return {"message": "Produit mis à jour"}
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    except Exception as e:
        logger.error(f"Erreur mise à jour produit 3up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/parfums-3up/{parfum_id}")
async def delete_parfum_3up_api(parfum_id: str):
    try:
        success = db.delete_parfum_3up(parfum_id)
        if success:
            return {"message": "Produit supprimé"}
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    except Exception as e:
        logger.error(f"Erreur suppression produit 3up: {e}")
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
        parfum = db.get_parfum(parfum_id)
        if not parfum:
            raise HTTPException(status_code=404, detail="Parfum non trouvé")
            
        engine = ZPLEngine(dpi=203)
        img_bytes = engine.generate_4up_preview_png(parfum)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Erreur preview 4-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/print-4up")
async def print_4up(request: Print4UpRequest, background_tasks: BackgroundTasks):
    global is_cancelled
    is_cancelled = False
    
    try:
        check_licence()
    except LicenceError as e:
        raise HTTPException(status_code=403, detail=str(e))
        
    try:
        # Normaliser : supporter l'ancien format (parfum_id unique) ET le nouveau (liste items)
        items_to_print = request.items
        if not items_to_print and request.parfum_id:
            items_to_print = [Print4UpItem(parfum_id=request.parfum_id, quantity=request.quantity)]
        
        if not items_to_print:
            raise HTTPException(status_code=400, detail="Aucun parfum à imprimer")

        engine = ZPLEngine(dpi=request.printer_dpi)

        # Détection B-EV4 : Gravigny ou TOSHIBA FLIPOU → pas de pitch dans XPML
        # (Validé terrain : la FLIPOU rejette aussi l'attribut pitch, comme la B-EV4 Gravigny)
        printer_info = next((p for p in db.get_printers() if p.get("ip") == request.printer_ip), {})
        xpml_pitch = printer_info.get("sector", "") != "Gravigny" and printer_info.get("name", "") != "TOSHIBA FLIPOU"
        is_bev4 = not xpml_pitch

        if is_bev4:
            offset_x = printer_info.get("offset_x_4up", request.offset_x)
            offset_y = printer_info.get("offset_y_4up", request.offset_y)
            d_param = printer_info.get("d_param_4up", None)
        else:
            offset_x = request.offset_x
            offset_y = request.offset_y
            d_param = None

        if request.printer_language != "TPCL":
            raise HTTPException(status_code=400, detail="ZPL non supporté pour ce format")

        styling = {
            "title_size": request.title_size, "title_bold": request.title_bold,
            "gs1_size": request.gs1_size, "gs1_bold": request.gs1_bold,
            "lot_size": request.lot_size, "lot_bold": request.lot_bold
        }

        # Send everything in a SINGLE TCP job using the batch engine
        total_bands = sum((item.quantity + 3) // 4 for item in items_to_print)
        
        # Le temps de maintien TCP doit couvrir le temps d'impression physique
        calc_sleep = max(2.0, total_bands * 0.5)
        
        batch_items = []
        total_qty = 0
        for item in items_to_print:
            parfum = db.get_parfum(item.parfum_id)
            if not parfum:
                raise HTTPException(status_code=404, detail=f"Parfum '{item.parfum_id}' non trouvé")
            
            nb_bands = (item.quantity + 3) // 4
            total_qty += item.quantity
            batch_items.append({"parfum": parfum, "qty": nb_bands})
            
        full_flux = engine.generate_4up_toshiba_tpcl_batch(batch_items, offset_x=offset_x, offset_y=offset_y, styling=styling, xpml_pitch=xpml_pitch, d_param=d_param)
        enqueue_job(request.printer_ip, request.printer_dpi, request.printer_language, full_flux, sleep_time=calc_sleep)
        jobs_enqueued = 1

        return {"message": f"Impression 4-up de {total_qty} étiquettes ({jobs_enqueued} jobs) ajoutée à la file d'attente."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur impression 4-up: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# FROMIS — Étiquettes allemandes 30x50mm
# ─────────────────────────────────────────────
FROMIS_LABELS_FILE = base_path / "etiquette_allemand" / "labels.json"

def _load_fromis_labels() -> dict:
    """Charge le JSON des étiquettes Fromis depuis le disque."""
    if FROMIS_LABELS_FILE.exists():
        with open(FROMIS_LABELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.get("/api/fromis/labels")
async def get_fromis_labels():
    """Retourne la liste des étiquettes Fromis disponibles."""
    labels = _load_fromis_labels()
    return {"labels": [{"name": k, "text_preview": v[:80] + "..." if len(v) > 80 else v} for k, v in sorted(labels.items())]}

@app.get("/api/fromis/preview/{label_name}")
async def preview_fromis_label(label_name: str):
    """Génère un aperçu PNG d'une étiquette Fromis."""
    labels = _load_fromis_labels()
    label_text = labels.get(label_name)
    if label_text is None:
        raise HTTPException(status_code=404, detail=f"Étiquette '{label_name}' non trouvée")
    try:
        engine = ZPLEngine(dpi=203)
        img_bytes = engine.generate_fromis_preview_png(label_text)
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PrintFromisRequest(BaseModel):
    printer_ip: str
    label_name: str
    quantity: int = 1

@app.post("/api/fromis/print")
async def print_fromis(request: PrintFromisRequest):
    """Impression d'une étiquette Fromis sur la Toshiba FLIPOU."""
    try:
        check_licence()
    except LicenceError as e:
        raise HTTPException(status_code=403, detail=str(e))

    labels = _load_fromis_labels()
    label_text = labels.get(request.label_name)
    if label_text is None:
        raise HTTPException(status_code=404, detail=f"Étiquette '{request.label_name}' non trouvée")

    if request.quantity <= 0 or request.quantity > 9999:
        raise HTTPException(status_code=400, detail="Quantité invalide (1 à 9999)")

    try:
        engine = ZPLEngine(dpi=203)
        # Format 3-up : 1 ligne = 3 étiquettes. On arrondit au supérieur.
        lignes = (request.quantity + 2) // 3
        flux = engine.generate_fromis_tpcl(label_text, lignes)
        
        # FLIPOU = B-EV4 → sleep de 2.0s minimum (validé terrain)
        enqueue_job(request.printer_ip, 203, "TPCL", flux, sleep_time=2.0)
        return {"message": f"{lignes * 3} étiquette(s) (soit {lignes} lignes) '{request.label_name}' envoyée(s) à l'imprimante."}
    except Exception as e:
        logger.error(f"Erreur impression Fromis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def find_ean13_for_libelle(libelle: str, parfums_list: list) -> tuple[str, str]:
    import unicodedata
    import re
    
    def normalize(s):
        s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower()
        s = re.sub(r'[^a-z0-9]', ' ', s)
        return s

    lib_norm = normalize(libelle)
    lib_words = set(lib_norm.split())
    
    best_match = None
    max_score = 0
    for p in parfums_list:
        p_norm = normalize(p.get('nom', ''))
        p_words = set(p_norm.split())
        
        score = len(lib_words.intersection(p_words))
        
        for flavor in ['vanille', 'abricot', 'fraise', 'citron', 'caramel', 'figue', 'nature', 'myrtille', 'chocolat', 'cafe', 'cerise', 'poire', 'mandarine', 'griotte']:
            if flavor in p_words and flavor in lib_words:
                score += 5
        
        if '2x125' in lib_norm.replace(' ', '') and '2x125' in p_norm.replace(' ', ''):
            score += 3
        if '4x125' in lib_norm.replace(' ', '') and '4x125' in p_norm.replace(' ', ''):
            score += 3
            
        if score > max_score:
            max_score = score
            best_match = p

    return best_match

@app.post("/print-json")
async def print_json(request: PrintJobRequest, background_tasks: BackgroundTasks):
    # La variable globale is_cancelled était dangereuse pour l'utilisation multi-utilisateur.
    # Pour l'instant, l'impression s'envoie en une fois. Si besoin, une gestion par job_id sera ajoutée.
    
    try:
        check_licence()
    except LicenceError as e:
        raise HTTPException(status_code=403, detail=str(e))
        
    engine = ZPLEngine(dpi=request.printer_dpi)
    printer = PrinterClient(host=request.printer_ip)
    lang = request.printer_language

    # Détecter si l'imprimante est sur le secteur Gravigny (B-EV4) ou si c'est la nouvelle B-EV4 (FLIPOU) :
    # La B-EV4 ET la TOSHIBA FLIPOU rejettent l'attribut pitch='120.1 mm' dans les balises sentinelles XPML.
    # (Validé par diagnostic juillet 2026 + commit 15eeb6a : la FLIPOU = firmware B-EV4, pas B-FV4D)
    printer_info = next((p for p in db.get_printers() if p.get("ip") == request.printer_ip), {})
    xpml_pitch = printer_info.get("sector", "") != "Gravigny" and printer_info.get("name", "") != "TOSHIBA FLIPOU"

    try:
        first_job = True
        full_flux = ""
        for ticket in request.items:
            
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
                
            styling = {
                "title_size": request.title_size, "title_bold": request.title_bold,
                "gs1_size": request.gs1_size, "gs1_bold": request.gs1_bold,
                "lot_size": request.lot_size, "lot_bold": request.lot_bold
            }
                
            if lang == "TPCL":
                # Chunking TPCL : limite de 2000 pour éviter le crash '{XS}'
                MAX_QTY_PER_JOB = 2000
                remaining = nb_rows
                while remaining > 0:
                    chunk_qty = min(remaining, MAX_QTY_PER_JOB)
                    flux = engine.generate_ticket_tpcl(ticket, quantity=chunk_qty, offset_x=request.offset_x, offset_y=request.offset_y, styling=styling, xpml_pitch=xpml_pitch)
                    full_flux += flux
                    remaining -= chunk_qty
            else:
                if request.printer_dpi == 203:
                    # Zebra Pots x2 (203 DPI) - Format 2-up avec code-barre EAN13
                    parfums_list = db.get_parfums() # use standard parfums list
                    match = find_ean13_for_libelle(ticket.libelle, parfums_list)
                    nom_match = match.get('nom', ticket.libelle) if match else ticket.libelle
                    ean13 = match.get('ean13', '0000000000000') if match else '0000000000000'
                    
                    # Le nb_rows correspond aux étiquettes unitaires. Vu que c'est du 2-up, on divise par 2.
                    # Ex: 1080 pots -> 1080 étiquettes unitaires -> 540 lignes imprimées
                    rows_to_print = (nb_rows + 1) // 2
                    if rows_to_print > 0:
                        flux = engine.generate_ticket_zebra_203_pots(nom_match, ean13, quantity=rows_to_print)
                        full_flux += flux
                else:
                    # Zebra Carton (300 DPI) - Format 1-up GS1-128
                    for _ in range(nb_rows):
                        flux = engine.generate_ticket_zebra_300(ticket, offset_x=request.offset_x, offset_y=request.offset_y, styling=styling)
                        full_flux += flux
                    
        # Envoi d'un seul énorme bloc pour éviter la lenteur réseau et les temps morts
        if full_flux:
            total_rows = sum((t.quantite + 2) // 3 if lang == "TPCL" else t.quantite for t in request.items)
            sleep_time = max(2.0, total_rows * 1.5)
            enqueue_job(request.printer_ip, request.printer_dpi, lang, full_flux, sleep_time)
            
        return {"message": f"Impression de {len(request.items)} produits ajoutée à la file d'attente."}

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
    return {"ready": ready, "details": status, "simulation": status.get("simulation", False)}

@app.get("/api/simulation-mode")
async def get_simulation_mode():
    return {"simulation_mode": settings.SIMULATION_MODE}

class SimulationModeRequest(BaseModel):
    enabled: bool

@app.post("/api/simulation-mode")
async def set_simulation_mode(req: SimulationModeRequest):
    settings.SIMULATION_MODE = req.enabled
    logger.info(f"Mode simulation passé à : {settings.SIMULATION_MODE}")
    return {"simulation_mode": settings.SIMULATION_MODE}

@app.get("/api/printers")
async def get_printers():
    return db.get_printers()

@app.post("/api/printers")
async def save_printers(printers: List[dict]):
    db.save_printers(printers)
    return {"message": "Configuration sauvegardée."}

@app.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    printer_ip: str = Form(...),
    printer_dpi: int = Form(...),
    printer_language: str = Form("ZPL")
):
    try:
        check_licence()
    except LicenceError as e:
        raise HTTPException(status_code=403, detail=str(e))

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
    format: str = "3up"

@app.post("/api/update-printer-offsets")
async def update_printer_offsets(req: PrinterOffsetsRequest):
    for field, val in [("gs1_size", req.gs1_size), ("lot_size", req.lot_size)]:
        if val != 0 and not (-10 <= val <= 40):
            raise HTTPException(
                status_code=422,
                detail=f"Valeur hors limites ({field}={val}). Delta attendu entre -10 et +40."
            )

    updated = db.update_printer_offsets(req.ip, {
        "offset_x": req.offset_x,
        "offset_y": req.offset_y,
        "title_size": req.title_size,
        "title_bold": req.title_bold,
        "gs1_size": req.gs1_size,
        "gs1_bold": req.gs1_bold,
        "lot_size": req.lot_size,
        "lot_bold": req.lot_bold
    }, format_type=req.format)
            
    if updated:
        return {"message": "Offsets sauvegardés"}
    else:
        raise HTTPException(status_code=404, detail="Imprimante non trouvée")

@app.get("/api/commande/{order_number}")
async def fetch_commande(order_number: str):
    """
    Interroge l'API Business Central en temps réel pour récupérer la commande.
    """
    check_licence() # Vérifie que le tool est autorisé
    
    try:
        from src.bc_client import BusinessCentralClient
        bc_client = BusinessCentralClient()
        return bc_client.fetch_sales_order(order_number)
    except FileNotFoundError:
        logger.warning("Fichier secret.json introuvable. Passage en mode simulation.")
    except Exception as e:
        logger.error(f"Erreur lors de l'appel Business Central: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur Business Central: {str(e)}")
    
    # Données fictives de secours uniquement si secret.json n'existe pas
    return [
        {
            "Client": "FERME DES PEUPLIERS (SIMULATION)",
            "Commande": order_number,
            "Libelle": "Yaourt Fraise 4x125gr",
            "DateLivraison": "16/07/2026",
            "Numlot": "A001",
            "Quantite": 10
        },
        {
            "Client": "FERME DES PEUPLIERS (SIMULATION)",
            "Commande": order_number,
            "Libelle": "Yaourt Vanille 4x125gr",
            "DateLivraison": "16/07/2026",
            "Numlot": "A001",
            "Quantite": 20
        }
    ]



@app.get("/api/stock/{libelle}")
async def get_stock_for_libelle(libelle: str, item_no: str = None):
    """Retourne la liste des lots pertinents avec quantité > 0 pour un produit (filtre sur item_no si fourni)."""
    try:
        from src.bc_client import BusinessCentralClient
        from datetime import datetime
        bc_client = BusinessCentralClient()
        token = bc_client.get_access_token()
        tenant_id = bc_client._config["BC_TENANT_ID"]
        env = bc_client._config.get("BC_ENVIRONMENT", "Production")
        company_name = bc_client._config.get("BC_COMPANY", "Ferme des Peupliers")
        
        stock_lots = bc_client._fetch_stock_lots(tenant_id, env, company_name, token, item_nos=[item_no] if item_no else None)
        
        candidates = bc_client._get_all_lots_for_libelle(libelle, stock_lots, datetime.now(), item_no=item_no)
        
        results = []
        for e in candidates:
            dlc_raw = e.get('Expiration_Date', '').split('T')[0]
            lot = e.get('Lot_No', '')
            qty = float(e.get('Remaining_Quantity', 0))
            
            # Formater la date en DD/MM/YYYY pour l'affichage, et YYMMDD pour le code barre
            try:
                dt_dlc = datetime.strptime(dlc_raw, "%Y-%m-%d")
                dlc_display = dt_dlc.strftime("%d/%m/%Y")
                code_barre_17 = dt_dlc.strftime("%y%m%d")
            except:
                dlc_display = dlc_raw
                code_barre_17 = ""
                
            # Vérifier si c'est bloqué qualité (soit par un champ, soit dans le nom du lot)
            blocked = "BLOQUE" in lot.upper() or e.get('Quality_Blocked', False)
            
            results.append({
                "lot": lot,
                "dlc_display": dlc_display,
                "code_barre_17": code_barre_17,
                "qty": qty,
                "blocked": blocked
            })
            
        return results
    except Exception as e:
        logger.error(f"Erreur API stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/licence")
async def api_licence():
    return get_licence_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
