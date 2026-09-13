from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import accounts, auth, business_profile, transactions

settings = get_settings()

app = FastAPI(
    title="HackMTY 2026 — Capital One",
    description="Backend base: envuelve la API de Nessie (o el mock) detrás de una sola interfaz.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # allow_credentials=False: la sesión viaja en el header Authorization, no en
    # cookies, así que no hace falta. Además es lo que vuelve peligroso un
    # CORS_ORIGINS mal puesto: con credentials activo, un origen de más puede
    # leer respuestas autenticadas.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """422 sin `input`.

    El handler default de FastAPI devuelve el valor que mandó el cliente dentro
    de cada error. En /auth/register eso significa que un body mal formado
    rebota la contraseña en claro en la respuesta — y los cuerpos 4xx son justo
    lo que acaba en Sentry, en un console.error o en un HAR compartido.
    """
    errors = [{k: v for k, v in error.items() if k != "input"} for error in exc.errors()]
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": errors}))

app.include_router(accounts.router)
app.include_router(auth.router)
app.include_router(business_profile.public_router)
app.include_router(business_profile.router)
app.include_router(transactions.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "nessie_mode": "mock" if settings.use_mock_nessie or not settings.nessie_api_key else "real",
    }
