"""
Fixtures compartidas de los tests.

Los tests de auth corren siempre contra MemoryUserStore, aunque el `.env` local
tenga USE_SNOWFLAKE=true. Razón: la suite tiene que pasar en la laptop de
cualquiera del equipo y en CI, donde no hay credenciales ni tabla `users`
creada. La ruta de Snowflake se cubre con el guard de esquema de test_auth.py,
que lee el SQL sin abrir conexión — misma idea que el guard que ya existía para
BusinessProfile.
"""

import asyncio

import pytest

from app.db import get_db
from app.db.sqlite_db import SqliteDatabase
from app.main import app
from app.models.schemas import StoredUser
from app.security import create_access_token, hash_password
from app.storage import get_store, get_user_store
from app.storage.memory_store import MemoryProfileStore, MemoryUserStore

# Un solo store para toda la sesión: app.dependency_overrides es global al `app`,
# así que si cada módulo de test registrara el suyo se pisarían entre ellos.
_USER_STORE = MemoryUserStore()
_PROFILE_STORE = MemoryProfileStore()
app.dependency_overrides[get_user_store] = lambda: _USER_STORE
# get_store también se sobrescribe: sin esto, con USE_SNOWFLAKE=true en el .env
# local la suite escribía en la tabla `business_profiles` REAL. Además de
# ensuciar los datos de la demo, esas filas salían por /business-profile/stats,
# que es público. Los tests nunca deben tocar Snowflake.
app.dependency_overrides[get_store] = lambda: _PROFILE_STORE
# Mismo criterio para el núcleo financiero: sqlite en memoria, nunca Snowflake.
_DB = SqliteDatabase(":memory:")
_DB.ensure_schema()
app.dependency_overrides[get_db] = lambda: _DB


@pytest.fixture
def db() -> SqliteDatabase:
    return _DB


@pytest.fixture
def user_store() -> MemoryUserStore:
    return _USER_STORE


def seed_user(
    user_id: str,
    username: str,
    password: str = "Contrasena123",
    business_name: str = "Negocio de prueba",
    full_name: str = "Persona de Prueba",
    birthdate: str = "1995-04-17",
) -> StoredUser:
    """Mete un usuario con user_id **fijo** en el store.

    Hace falta porque /auth/register genera un uuid aleatorio, y los tests de
    business-profile necesitan owner_id determinista para poder armar el token
    y comparar lo que se guardó bajo ese dueño.
    """
    user = StoredUser(
        user_id=user_id,
        username=username,
        business_name=business_name,
        full_name=full_name,
        birthdate=birthdate,
        password_hash=hash_password(password),
    )
    # create_user es async por la interfaz, pero MemoryUserStore no hace I/O:
    # asyncio.run aquí deja que los tests sigan siendo funciones sync normales.
    asyncio.run(_USER_STORE.create_user(user))
    return user


def auth_headers(user_id: str) -> dict[str, str]:
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}
