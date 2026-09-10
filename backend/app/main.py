from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import accounts, transactions

settings = get_settings()

app = FastAPI(
    title="HackMTY 2026 — Capital One",
    description="Backend base: envuelve la API de Nessie (o el mock) detrás de una sola interfaz.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(transactions.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "nessie_mode": "mock" if settings.use_mock_nessie or not settings.nessie_api_key else "real",
    }
