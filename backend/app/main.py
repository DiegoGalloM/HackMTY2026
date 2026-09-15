import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import get_db
from app.observability import init_error_tracking, unhandled_exception_handler
from app.routers import (
    accounts,
    auth,
    business_profile,
    checkout,
    demo,
    finance,
    health,
    transactions,
)
from app.storage.audio_store import OnboardingAudioStore

settings = get_settings()
# Antes de crear la app: así la integración de Sentry con FastAPI se engancha
# desde el primer request. Sin SENTRY_DSN no hace nada.
init_error_tracking(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara los negocios de ejemplo al arrancar, para que sus credenciales
    sirvan en *Iniciar sesión* desde el primer momento.

    En segundo plano a propósito: con Snowflake la primera siembra tarda unos
    segundos por negocio y bloquear el arranque haría fallar el health check
    del despliegue. En sqlite termina en un par de segundos, mucho antes de
    que alguien alcance a escribir sus credenciales.
    """
    tasks = [asyncio.create_task(demo.provision_all()), asyncio.create_task(_purge_expired_audio())]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()


async def _purge_expired_audio() -> None:
    """Borra el audio de la encuesta ya vencido. El demo gratis se reinicia
    seguido y a veces nadie inicia sesión en días: sin esto, un audio vencido
    esperaría a la siguiente encuesta o login para borrarse."""
    try:
        store = OnboardingAudioStore(get_db(), settings.onboarding_audio_retention_days)
        await asyncio.to_thread(store.purge_expired)
    except Exception:  # nunca tumbar el arranque por la limpieza
        logging.getLogger("uvicorn.error").exception("No se pudo purgar el audio vencido de la encuesta")


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
    # El frontend desplegado vive en otro origen: sin exponerlo, el navegador
    # esconde Retry-After y la app no puede decir cuánto esperar tras un 429.
    expose_headers=["Retry-After"],
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


# Cualquier error no controlado: 500 con error_id, sin stack trace al cliente.
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(accounts.router)
app.include_router(auth.router)
app.include_router(business_profile.public_router)
app.include_router(business_profile.router)
app.include_router(transactions.router)
app.include_router(finance.router)
app.include_router(checkout.router)
app.include_router(demo.public_router)
app.include_router(demo.router)
app.include_router(health.router)
