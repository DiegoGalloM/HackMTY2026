import asyncio

from fastapi import APIRouter, Depends

from app.db import get_db
from app.db.base import Database
from app.finance import cache
from app.finance.accounting import AccountingService
from app.finance.repo import Repo
from app.models.schemas import BusinessProfile
from app.routers.deps import require_owner
from app.storage import get_store
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


@router.post("")
async def save_profile(
    owner_id: str,
    profile: BusinessProfile,
    store: ProfileStore = Depends(get_store),  # noqa: B008
    db: Database = Depends(get_db),  # noqa: B008
):
    await store.save_profile(owner_id, profile)
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
):
    return await store.get_profile(owner_id)


@public_router.get("/stats/{category}")
async def get_category_stats(category: str, store: ProfileStore = Depends(get_store)):  # noqa: B008
    # PÚBLICO a propósito: alimenta la comparativa que se le muestra al usuario
    # antes de registrarse. Solo sale el agregado, y solo si la cohorte es lo
    # bastante grande para que ningún negocio sea identificable dentro de ella.
    stats = await store.category_stats(category)
    if stats.get("n_negocios", 0) < MIN_COHORT:
        return {**stats, "answers_pct_true": {}, "below_min_cohort": True}
    return stats
