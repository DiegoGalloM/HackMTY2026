import asyncio

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.db import get_db
from app.db.base import Database
from app.finance import cache
from app.finance.accounting import AccountingService
from app.finance.repo import Repo
from app.models.schemas import BusinessProfile
from app.ratelimit import rate_limit
from app.routers.deps import require_owner
from app.storage import get_store
from app.storage.audio_store import OnboardingAudioStore
from app.storage.base import ProfileStore

# Tamaño mínimo de cohorte para publicar porcentajes. Con n=1 cada porcentaje
# ES la respuesta literal de ese negocio, y la categoría la escribe el usuario,
# así que basta con inventar una categoría rara para tener una cohorte de uno y
# leer sus respuestas sin token. Debajo del umbral se regresa el conteo pero no
# el desglose.
MIN_COHORT = 5


# `require_owner` se importa de routers/deps.py y se re-exporta desde aquí:
# es la misma guardia para el perfil y para toda la API financiera.
__all__ = ["MIN_COHORT", "public_router", "require_owner", "router"]


# Dos routers en vez de uno: la autorización va en el prefijo `{owner_id}`, así
# que toda ruta que se agregue a `router` nace protegida. Antes el Depends se
# ponía a mano en cada endpoint y una ruta nueva se quedaba abierta sin que
# nadie lo notara.
router = APIRouter(
    prefix="/business-profile/{owner_id}",
    tags=["business-profile"],
    dependencies=[Depends(require_owner)],
)

public_router = APIRouter(prefix="/business-profile", tags=["business-profile"])


def get_audio_store(db: Database = Depends(get_db)) -> OnboardingAudioStore:  # noqa: B008
    return OnboardingAudioStore(db, get_settings().onboarding_audio_retention_days)


# Campos del audio: llegan en el POST (el contrato con el frontend no cambia)
# pero NO se guardan en la fila del perfil ni se regresan en el GET.
AUDIO_FIELDS = {"week_description_audio_base64": None, "week_description_audio_mime": None}


@router.post("")
async def save_profile(
    owner_id: str,
    profile: BusinessProfile,
    store: ProfileStore = Depends(get_store),  # noqa: B008
    db: Database = Depends(get_db),  # noqa: B008
    audio: OnboardingAudioStore = Depends(get_audio_store),  # noqa: B008
):
    # La voz de quien prueba el demo va a su propia tabla con caducidad
    # (ONBOARDING_AUDIO_RETENTION_DAYS); a la fila del perfil llega sin audio.
    await asyncio.to_thread(
        audio.save, owner_id, profile.week_description_audio_base64, profile.week_description_audio_mime
    )
    await asyncio.to_thread(audio.maybe_purge_expired)
    await store.save_profile(owner_id, profile.model_copy(update=AUDIO_FIELDS))
    cache.invalidate(("profile", id(store), owner_id))
    # El onboarding no es una encuesta aislada: con la categoría se inicializa
    # el catálogo de cuentas del negocio (idempotente si ya existía).
    await asyncio.to_thread(
        lambda: AccountingService(Repo(db, owner_id)).ensure_chart_of_accounts(profile.category)
    )
    return {"status": "ok"}


@router.get("")
async def get_profile(
    owner_id: str,
    store: ProfileStore = Depends(get_store),  # noqa: B008
    audio: OnboardingAudioStore = Depends(get_audio_store),  # noqa: B008
):
    # El GET se llama en cada inicio de sesión: es el lugar natural para que el
    # audio vencido se borre aunque nadie vuelva a hacer la encuesta.
    await asyncio.to_thread(audio.maybe_purge_expired)
    profile = await store.get_profile(owner_id)
    # Un perfil guardado antes de la Fase 5 puede traer audio en la fila: nunca
    # se devuelve (se limpia con scripts/purge_legacy_profile_audio.py).
    return profile.model_copy(update=AUDIO_FIELDS) if profile else None


@public_router.get("/stats/{category}", dependencies=[Depends(rate_limit("stats"))])
async def get_category_stats(category: str, store: ProfileStore = Depends(get_store)):  # noqa: B008
    # PÚBLICO a propósito: alimenta la comparativa que se le muestra al usuario
    # antes de registrarse. Solo sale el agregado, y solo si la cohorte es lo
    # bastante grande para que ningún negocio sea identificable dentro de ella.
    stats = await store.category_stats(category)
    if stats.get("n_negocios", 0) < MIN_COHORT:
        return {**stats, "answers_pct_true": {}, "below_min_cohort": True}
    return stats
