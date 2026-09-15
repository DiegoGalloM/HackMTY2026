import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import (
    accounts,
    auth,
    business_profile,
    checkout,
    demo,
    finance,
    transactions,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara los negocios de ejemplo al arrancar, para que sus credenciales
    sirvan en *Iniciar sesión* desde el primer momento.

    En segundo plano a propósito: con Snowflake la primera siembra tarda unos
    segundos por negocio y bloquear el arranque haría fallar el health check
    del despliegue. En sqlite termina en un par de segundos, mucho antes de
    que alguien alcance a escribir sus credenciales.
    """
    task = asyncio.create_task(demo.provision_all())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    lifespan=lifespan,
    title="Capital One Business — HackMTY 2026",
    description=(
        "Inteligencia de flujo de efectivo y capital de trabajo para micro-negocios: "
        "ventas por QR, inventario con recetas, contabilidad de partida doble, estados "
        "financieros, razones y un asistente que responde con los datos reales del negocio.\n\n"
        "**Demo de HackMTY 2026:** todas las transacciones son simuladas; no se procesa "
        "dinero real ni se conecta a cuentas bancarias reales. No es un producto de "
        "Capital One ni está afiliado, respaldado o patrocinado por Capital One, N.A."
    ),
    version="0.2.0",
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
app.include_router(finance.router)
app.include_router(checkout.router)
app.include_router(demo.public_router)
app.include_router(demo.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "nessie_mode": "mock" if settings.use_mock_nessie or not settings.nessie_api_key else "real",
        "storage": "snowflake" if settings.use_snowflake and settings.snowflake_account else "memory",
        "payment_provider": settings.payment_provider,
        "transaction_provider": settings.transaction_provider,
    }
