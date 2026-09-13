"""
Demo: entrar con un negocio de ejemplo ya sembrado, o sembrar el propio.

POST /demo/session   crea (o reutiliza) la cuenta demo, guarda su perfil de
                     onboarding, siembra la panadería si está vacía y regresa
                     la misma AuthResponse que /auth/login.
POST /business/{owner_id}/demo/seed   siembra la historia de ejemplo en el
                     negocio del usuario autenticado (para cuentas nuevas).
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

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

public_router = APIRouter(prefix="/demo", tags=["demo"])
router = APIRouter(prefix="/business/{owner_id}/demo", tags=["demo"], dependencies=[Depends(require_owner)])


@public_router.post("/session", response_model=AuthResponse)
async def demo_session(
    users: UserStore = Depends(get_user_store),  # noqa: B008
    store: ProfileStore = Depends(get_store),  # noqa: B008
    db: Database = Depends(get_db),  # noqa: B008
):
    user = await users.get_user_by_username(demo.DEMO_USERNAME)
    if user is None:
        user = StoredUser(
            user_id=uuid.uuid4().hex,
            username=demo.DEMO_USERNAME,
            business_name=demo.DEMO_BUSINESS_NAME,
            full_name=demo.DEMO_FULL_NAME,
            birthdate=demo.DEMO_BIRTHDATE,
            password_hash=await asyncio.to_thread(hash_password, demo.DEMO_PASSWORD),
        )
        if not await users.create_user(user):
            user = await users.get_user_by_username(demo.DEMO_USERNAME)
            if user is None:  # pragma: no cover - carrera improbable
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="demo_user_unavailable")
    if await store.get_profile(user.user_id) is None:
        await store.save_profile(user.user_id, BusinessProfile(**demo.DEMO_PROFILE))
    seeder = demo.DemoSeeder(db, user.user_id)
    await run(seeder.seed, False)
    return _auth_response(user)


@router.post("/seed")
async def seed_my_business(reset: bool = False, ctx: FinanceContext = Depends(get_finance_context)):  # noqa: B008
    seeder = demo.DemoSeeder(ctx.db, ctx.business_id)
    result = await run(seeder.seed, reset)
    return jsonable(result)
