"""
Registro, login y validación de token.

`get_current_user` es la dependencia reutilizable: cualquier endpoint que ponga
`Depends(get_current_user)` ya queda protegido y recibe el StoredUser.
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.finance import cache
from app.models.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    StoredUser,
    UserPublic,
)
from app.ratelimit import rate_limit
from app.security import (
    create_access_token,
    decode_access_token,
    dummy_verify,
    hash_password,
    validate_password,
    verify_password,
)
from app.storage import get_user_store
from app.storage.base import UserStore

router = APIRouter(prefix="/auth", tags=["auth"])

# auto_error=False para poder responder siempre el mismo 401 "invalid_token";
# con el default, un header ausente da 403 y un header mal formado 401, y el
# frontend tendría que distinguir dos casos que para él son lo mismo.
_bearer = HTTPBearer(auto_error=False)

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid_token",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    users: UserStore = Depends(get_user_store),  # noqa: B008
) -> StoredUser:
    if credentials is None or not credentials.credentials:
        raise _INVALID_TOKEN

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise _INVALID_TOKEN

    # El token puede estar bien firmado y vigente pero apuntar a un usuario que
    # ya no existe (borrado, o store en memoria reiniciado): también es 401.
    # El usuario se cachea unos minutos: se resuelve en CADA request y en
    # Snowflake cuesta ~0.4 s; un usuario inexistente nunca se cachea.
    user_id = payload.get("sub", "")
    key = ("user", id(users), user_id)
    user = cache.get(key, lambda: None)
    if user is None:
        user = await users.get_user_by_id(user_id)
        if user is not None:
            cache.get(key, lambda: user)
    if user is None:
        raise _INVALID_TOKEN

    return user


def _auth_response(user: StoredUser) -> AuthResponse:
    token, expires_in = create_access_token(user.user_id)
    return AuthResponse(access_token=token, expires_in=expires_in, user=user.to_public())


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit("auth_register"))])
async def register(
    payload: RegisterRequest,
    users: UserStore = Depends(get_user_store),  # noqa: B008
):
    # La política se revisa antes de tocar el store: así una contraseña débil no
    # gasta una consulta y, más importante, el 400 no depende de si el username
    # existe (no se filtra información).
    problems = validate_password(payload.password, payload.username)
    if problems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "weak_password", "problems": problems},
        )

    user = StoredUser(
        # uuid en vez del username como id: el username es lo único que el
        # usuario podría querer cambiar después, y el id ya vive en tokens y en
        # los perfiles de negocio.
        user_id=uuid.uuid4().hex,
        username=payload.username,
        business_name=payload.business_name,
        full_name=payload.full_name,
        birthdate=payload.birthdate,
        # bcrypt va en un hilo aparte: cuesta ~265 ms a propósito (es su chiste),
        # y estos endpoints son `async def`, o sea que corren EN el event loop.
        # Sin to_thread, ~4 registros/logins por segundo dejan al worker al 100%
        # y congelan todas las demás requests, incluido /health. Es el mismo
        # patrón que ya usa snowflake_store para no bloquear el loop.
        password_hash=await asyncio.to_thread(hash_password, payload.password),
    )

    if not await users.create_user(user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username_taken")

    return _auth_response(user)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(rate_limit("auth_login"))])
async def login(
    payload: LoginRequest,
    users: UserStore = Depends(get_user_store),  # noqa: B008
):
    user = await users.get_user_by_username(payload.username)

    if user is None:
        # Se verifica contra un hash de relleno para que el tiempo de respuesta
        # sea parecido al de un usuario real; si no, medir la latencia revelaría
        # qué usernames existen. En hilo aparte, igual que el verify de abajo.
        await asyncio.to_thread(dummy_verify)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        )

    if not await asyncio.to_thread(verify_password, payload.password, user.password_hash):
        # Mismo status y mismo detail que arriba, a propósito.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials"
        )

    return _auth_response(user)


@router.get("/me", response_model=UserPublic)
async def me(current_user: StoredUser = Depends(get_current_user)):  # noqa: B008
    return current_user.to_public()
