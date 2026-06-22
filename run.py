import uvicorn
from src.config import settings

if __name__ == "__main__":
    print(f"--- Lancement de Scaly-Ticket sur http://{settings.API_HOST}:{settings.API_PORT} ---")
    uvicorn.run("src.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
