"""
Demo: entrar con un negocio de ejemplo ya sembrado, o sembrar el propio.

POST /demo/session   crea (o reutiliza) la cuenta del negocio demo elegido
                     ({"business": "panaderia" | "estetica"}, default la
                     panadería; sin cuerpo sigue funcionando), guarda su perfil
                     de onboarding si falta, siembra la historia si está vacía
                     y regresa la misma AuthResponse que /auth/login.
POST /business/{owner_id}/demo/seed   siembra la historia de ejemplo elegida
                     (?business=) en el negocio del usuario autenticado.

`provision_all()` corre al arrancar el backend (ver app/main.py) para que las
credenciales de la demo sirvan en *Iniciar sesión* sin que nadie haya pulsado
antes "Explorar la demo": los stores en memoria arrancan vacíos y, hasta que
existiera la cuenta, ese login respondía 401.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.db import get_db
from app.db.base import Database
from app.finance import demo
from app.finance.deps import FinanceContext, get_finance_context, run
from app.models.finance import jsonable
from app.models.schemas import AuthResponse, BusinessProfile, StoredUser
from app.routers.auth import _auth_response
from app.routers.deps import require_owner
from app.security import hash_password
from app.storage import get_store, get_user_store
from app.storage.base import ProfileStore, UserStore

# "uvicorn.error" y no `__name__`: uvicorn sólo instala handlers en sus
# propios loggers, así que un logger de la app no se vería en la terminal —
# y este aviso importa cuando la siembra en Snowflake tarda unos segundos.
log = logging.getLogger("uvicorn.error")

public_router = APIRouter(prefix="/demo", tags=["demo"])
router = APIRouter(prefix="/business/{owner_id}/demo", tags=["demo"], dependencies=[Depends(require_owner)])

DemoKey = Literal["panaderia", "estetica"]


class DemoSessionRequest(BaseModel):
    business: DemoKey = demo.DEFAULT_DEMO_BUSINESS


async def provision(
    business: demo.DemoBusiness,
    users: UserStore,
    store: ProfileStore,
    db: Database,
) -> StoredUser:
    """Deja listo un negocio de ejemplo: cuenta, perfil de onboarding e
    historia. Idempotente: sólo crea lo que falte y no vuelve a sembrar."""
    user = await users.get_user_by_username(business.username)
    if user is None:
        user = StoredUser(
            user_id=uuid.uuid4().hex,
            username=business.username,
            business_name=business.business_name,
            full_name=business.full_name,
            birthdate=business.birthdate,
            password_hash=await asyncio.to_thread(hash_password, business.password),
        )
        if not await users.create_user(user):
            # Carrera: alguien más lo creó entre la lectura y la escritura.
            user = await users.get_user_by_username(business.username)
            if user is None:  # pragma: no cover - improbable
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="demo_user_unavailable")
    if await store.get_profile(user.user_id) is None:
        await store.save_profile(user.user_id, BusinessProfile(**business.profile))
    await run(demo.DemoSeeder(db, user.user_id, business).seed, False)
    return user


async def provision_all() -> None:
    """Los dos negocios de ejemplo, al arrancar. Un fallo aquí no puede tumbar
    el backend: la demo se puede aprovisionar después desde /demo/session."""
    users, store, db = get_user_store(), get_store(), get_db()
    for business in demo.DEMO_BUSINESSES.values():
        try:
            await provision(business, users, store, db)
            log.info("Negocio demo listo: %s (%s)", business.business_name, business.username)
        except Exception as exc:  # noqa: BLE001 - la demo es un extra, no un requisito de arranque
            log.warning("No se pudo preparar el negocio demo %s: %s", business.key, exc)


@public_router.get("/businesses")
async def list_demo_businesses():
    """Los negocios de ejemplo disponibles (sin credenciales)."""
    return [
        {"key": b.key, "business_name": b.business_name, "full_name": b.full_name, "category": b.category, "place": b.place, "tagline": b.tagline}
        for b in demo.DEMO_BUSINESSES.values()
    ]


@public_router.post("/session", response_model=AuthResponse)
async def demo_session(
    payload: DemoSessionRequest | None = None,
    users: UserStore = Depends(get_user_store),  # noqa: B008
    store: ProfileStore = Depends(get_store),  # noqa: B008
    db: Database = Depends(get_db),  # noqa: B008
):
    business = demo.DEMO_BUSINESSES[(payload or DemoSessionRequest()).business]
    return _auth_response(await provision(business, users, store, db))


@router.post("/seed")
async def seed_my_business(
    reset: bool = False,
    business: DemoKey = Query(demo.DEFAULT_DEMO_BUSINESS),  # noqa: B008
    ctx: FinanceContext = Depends(get_finance_context),  # noqa: B008
):
    seeder = demo.DemoSeeder(ctx.db, ctx.business_id, business)
    result = await run(seeder.seed, reset)
    return jsonable(result)
