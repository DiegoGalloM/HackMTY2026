from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.schemas import BusinessProfile, StoredUser
from app.routers.auth import get_current_user
from app.storage import get_store
from app.storage.base import ProfileStore

# Tamaño mínimo de cohorte para publicar porcentajes. Con n=1 cada porcentaje
# ES la respuesta literal de ese negocio, y la categoría la escribe el usuario,
# así que basta con inventar una categoría rara para tener una cohorte de uno y
# leer sus respuestas sin token. Debajo del umbral se regresa el conteo pero no
# el desglose.
MIN_COHORT = 5


async def require_owner(
    owner_id: str = Path(...),
    current_user: StoredUser = Depends(get_current_user),  # noqa: B008
) -> StoredUser:
    """El perfil de un negocio solo lo toca su dueño.

    `owner_id` se declara con `Path(...)` a propósito: sin eso FastAPI lo
    resolvería como query param en cualquier ruta que no tenga un `{owner_id}`
    en su path, y entonces `?owner_id=<el mío>` pasaría el check mientras la
    ruta opera sobre el perfil de otro.
    """
    if current_user.user_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_owner")
    return current_user


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
):
    await store.save_profile(owner_id, profile)
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
