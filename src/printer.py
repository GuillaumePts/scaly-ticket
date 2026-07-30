import socket
import logging
import time
from src.config import settings

logger = logging.getLogger(__name__)

class PrinterClient:
    def __init__(self, host: str, port: int = 9100):
        self.host = host
        self.port = port

    def get_status(self) -> dict:
        """Récupère le statut de l'imprimante via ~HS (Zebra) ou via Socket TCP."""
        # Pour les imprimantes locales ou non-IP, on retourne un statut par défaut
        if not self.host or "." not in self.host or self.host == "0.0.0.0":
            return {"paper_out": False, "pause": False, "ribbon_out": False, "head_open": False}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                # 1. Test de la connexion physique (Ping TCP)
                try:
                    s.connect((self.host, self.port))
                except Exception as e:
                    logger.warning(f"Impossible de se connecter à {self.host}: {e}")
                    return {"error": f"Hors ligne ou débranchée"}
                    
                # 2. Si connecté, on tente le statut Zebra natif
                try:
                    s.sendall(b"~HS")
                    response = s.recv(1024).decode("utf-8")
                    return self._parse_hs_response(response)
                except (TimeoutError, socket.timeout):
                    # Si timeout ici, c'est que l'imprimante est bien branchée et répond au Ping, 
                    # mais elle ne parle pas le langage Zebra (ex: Toshiba muette). C'est normal.
                    logger.info(f"L'imprimante {self.host} est en ligne mais muette au ~HS.")
                    return {"paper_out": False, "pause": False, "ribbon_out": False, "head_open": False, "status": "unknown"}
                    
        except Exception as e:
            logger.warning(f"Erreur globale socket sur {self.host}: {e}")
            return {"error": str(e)}

    def is_ready(self) -> bool:
        """Vérifie si l'imprimante est prête à recevoir un job."""
        status = self.get_status()
        if "error" in status:
            return True # Par défaut on tente quand même l'envoi si le statut échoue
        
        ready = not (status.get("paper_out") or status.get("pause") or 
                     status.get("ribbon_out") or status.get("head_open"))
        return ready

    def wait_until_ready(self, timeout: int = 30):
        """Attend que l'imprimante soit prête avant de continuer."""
        if not self.host or "." not in self.host or self.host == "0.0.0.0":
            return True
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status()
            if "error" not in status:
                if not (status.get("paper_out") or status.get("pause") or 
                        status.get("ribbon_out") or status.get("head_open")):
                    return True
                logger.warning(f"Imprimante {self.host} occupée ou en erreur : {status}. Attente...")
            time.sleep(2)
        return True # On continue même après timeout pour ne pas bloquer la prod

    def send_zpl(self, zpl: str, sleep_time: float = 2.0):
        """Envoie le flux (ZPL ou TPCL) à l'imprimante via Socket TCP."""
        if not self.host or self.host == "0.0.0.0":
            logger.error("Adresse IP de l'imprimante non configurée.")
            return

        try:
            # Detect if the payload contains TPCL/XPML commands
            is_tpcl = ("<xpml>" in zpl) or ("{C|}" in zpl) or (zpl.startswith("\x1b"))
            
            max_retries = 3 if is_tpcl else 1
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(10.0 if is_tpcl else 5.0)
                        s.connect((self.host, self.port))
                        s.sendall(zpl.encode("latin-1")) # latin-1 ou utf-8 selon les besoins
                        
                        if is_tpcl:
                            logger.info(f"Flux TPCL détecté. Maintien de la connexion (ESTABLISHED) pendant {sleep_time}s...")
                            time.sleep(sleep_time)
                            # Fermeture propre APRÈS le délai pour éviter le timeout CLOSE_WAIT de l'imprimante
                            try:
                                s.shutdown(socket.SHUT_WR)
                            except OSError:
                                pass
                            
                        logger.info(f"Flux envoyé avec succès via TCP à {self.host}")
                        return # Succès, on sort de la fonction
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Tentative {retry_count}/{max_retries} échouée pour {self.host}: {e}")
                    if retry_count >= max_retries:
                        raise # On relève l'erreur si on a épuisé les essais
                    time.sleep(2.0) # Attente avant le prochain essai
                    
        except Exception as e:
            logger.error(f"Erreur fatale lors de l'envoi TCP à {self.host}: {e}")
            raise

    def _parse_hs_response(self, response: str) -> dict:
        """Parse la réponse ~HS de Zebra."""
        clean_resp = response.replace("\x02", "").replace("\x03", "")
        lines = clean_resp.split("\r\n")
        if not lines or not lines[0]:
            return {"error": "Empty response"}
        
        parts = lines[0].split(",")
        if len(parts) < 12:
            return {"error": "Malformed response"}

        return {
            "paper_out": parts[1] == "1",
            "pause": parts[2] == "1",
            "ribbon_out": parts[8] == "1",
            "head_open": parts[9] == "1",
        }
