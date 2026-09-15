"""
Tests de registro / login / token.

Corren contra MemoryUserStore (ver conftest.py). El último test es un guard de
esquema al estilo del de BusinessProfile: revisa el SQL de SnowflakeUserStore y
el archivo de migración **sin conectarse a Snowflake**, para que agregar un campo
a StoredUser sin agregar la columna truene aquí y no en la demo.
"""

import asyncio
import inspect
import re
import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.models.schemas import StoredUser
from app.security import verify_password
from app.storage import snowflake_store
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

VALID_REGISTRATION = {
    "username": "dona_tere",
    "business_name": "Tortas Doña Tere",
    "full_name": "Teresa Ramírez",
    "birthdate": "1984-03-11",
    "password": "TortasRicas9",
}


def _register(**overrides):
    """Cada test necesita un username propio: el store vive toda la sesión."""
    return client.post("/auth/register", json={**VALID_REGISTRATION, **overrides})


def _json_contains_key(payload, needle: str) -> bool:
    """Busca una llave en cualquier nivel del JSON — así el test de fuga de
    password no depende de dónde esté anidado el objeto user."""
    if isinstance(payload, dict):
        return any(k == needle or _json_contains_key(v, needle) for k, v in payload.items())
    if isinstance(payload, list):
        return any(_json_contains_key(item, needle) for item in payload)
    return False


# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------

def test_register_returns_token_and_public_user():
    response = _register(username="reg_happy")
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert isinstance(body["expires_in"], int) and body["expires_in"] > 0

    user = body["user"]
    assert user["username"] == "reg_happy"
    assert user["business_name"] == VALID_REGISTRATION["business_name"]
    assert user["full_name"] == VALID_REGISTRATION["full_name"]
    assert user["birthdate"] == VALID_REGISTRATION["birthdate"]
    assert user["user_id"]
    # El contrato con el frontend es exactamente este set de llaves.
    assert set(user) == {"user_id", "username", "business_name", "full_name", "birthdate"}


def test_register_response_never_leaks_password():
    response = _register(username="reg_noleak")
    body = response.json()

    for forbidden in ("password", "password_hash", "hash"):
        assert not _json_contains_key(body, forbidden), f"el JSON expone '{forbidden}'"
    assert VALID_REGISTRATION["password"] not in response.text


def test_register_stores_a_hash_not_the_plaintext(user_store):
    plaintext = "MiClaveSegura7"
    _register(username="reg_hash", password=plaintext)

    stored = asyncio.run(user_store.get_user_by_username("reg_hash"))
    assert stored is not None
    assert stored.password_hash != plaintext
    assert plaintext not in stored.password_hash
    assert verify_password(plaintext, stored.password_hash) is True
    assert verify_password("otraClaveDistinta1", stored.password_hash) is False


def test_register_normalizes_username_to_lowercase_and_trimmed():
    response = _register(username="  MaYuScUlAs_Y_Espacios  ")
    assert response.status_code == 201, response.text
    assert response.json()["user"]["username"] == "mayusculas_y_espacios"


@pytest.mark.parametrize(
    ("password", "expected_code"),
    [
        ("Corta9", "too_short"),
        ("A" + "a" * 130 + "9", "too_long"),
        ("TODOMAYUSCULAS9", "missing_lowercase"),
        ("todominusculas9", "missing_uppercase"),
        ("SinNumerosAqui", "missing_digit"),
        ("Pass_weakuser_9", "contains_username"),
    ],
)
def test_weak_password_returns_400_with_exact_code(password, expected_code):
    response = client.post(
        "/auth/register",
        json={**VALID_REGISTRATION, "username": "weakuser", "password": password},
    )
    assert response.status_code == 400, response.text

    detail = response.json()["detail"]
    assert detail["code"] == "weak_password"
    assert expected_code in detail["problems"]


def test_contains_username_is_case_insensitive():
    response = client.post(
        "/auth/register",
        json={**VALID_REGISTRATION, "username": "panaderia", "password": "XPANADERIAx9"},
    )
    assert response.status_code == 400
    assert "contains_username" in response.json()["detail"]["problems"]


@pytest.mark.parametrize(
    "duplicate",
    ["dup_user", "DUP_USER", "  dup_user  ", "  Dup_User  "],
    ids=["exacto", "mayusculas", "con_espacios", "mayusculas_y_espacios"],
)
def test_duplicate_username_returns_409(duplicate):
    first = _register(username="dup_user")
    assert first.status_code in (201, 409)  # el primer parámetro lo crea

    response = _register(username=duplicate)
    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "username_taken"}


@pytest.mark.parametrize(
    "bad_username",
    ["ab", "a" * 33, "con espacio", "MAYUS@simbolo", "acentúa", ""],
)
def test_invalid_username_shape_returns_422(bad_username):
    response = _register(username=bad_username)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "bad_birthdate",
    ["no-es-fecha", "2020-13-45", "11/03/1984", "2099-01-01", "1800-01-01", ""],
)
def test_invalid_birthdate_returns_422(bad_birthdate):
    response = _register(username="fecha_mala", birthdate=bad_birthdate)
    assert response.status_code == 422, response.text


def test_minor_cannot_register():
    """La regla de edad (>=18) es de negocio pero se valida en el schema, así que
    sale como 422 igual que una fecha con formato malo."""
    from datetime import UTC, datetime, timedelta

    # Con timedelta y no replace(year=...): un 29 de febrero, "hace 10 años"
    # con replace no existe y el test tronaba con ValueError.
    today = datetime.now(UTC).date()
    recent = (today - timedelta(days=10 * 365)).isoformat()
    assert _register(username="menor_edad", birthdate=recent).status_code == 422


@pytest.mark.parametrize("blank_field", ["business_name", "full_name"])
def test_blank_required_text_fields_return_422(blank_field):
    response = _register(username="blanco", **{blank_field: "   "})
    assert response.status_code == 422, response.text


# --------------------------------------------------------------------------
# Login
# --------------------------------------------------------------------------

def test_login_ok_returns_usable_token():
    _register(username="login_ok", password="ClaveBuena12")

    response = client.post("/auth/login", json={"username": "login_ok", "password": "ClaveBuena12"})
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "login_ok"
    assert not _json_contains_key(body, "password_hash")

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "login_ok"


def test_login_accepts_uppercase_and_padded_username():
    _register(username="login_norm", password="ClaveBuena12")
    response = client.post(
        "/auth/login", json={"username": "  LOGIN_NORM  ", "password": "ClaveBuena12"}
    )
    assert response.status_code == 200, response.text


def test_wrong_password_and_unknown_user_are_indistinguishable():
    """No se le dice al atacante si el usuario existe: mismo status y mismo body."""
    _register(username="login_enum", password="ClaveBuena12")

    wrong_password = client.post(
        "/auth/login", json={"username": "login_enum", "password": "ClaveEquivocada12"}
    )
    unknown_user = client.post(
        "/auth/login", json={"username": "no_existe_nadie", "password": "ClaveBuena12"}
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"detail": "invalid_credentials"}


# --------------------------------------------------------------------------
# /auth/me y validación de token
# --------------------------------------------------------------------------

def test_me_returns_public_user_with_fresh_token():
    token = _register(username="me_ok").json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert set(response.json()) == {
        "user_id", "username", "business_name", "full_name", "birthdate",
    }


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer basura"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "no-es-un-scheme"},
    ],
    ids=["sin_header", "token_basura", "token_vacio", "scheme_basic", "sin_scheme"],
)
def test_me_rejects_bad_authorization_header(headers):
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401, response.text
    assert response.json() == {"detail": "invalid_token"}


def test_me_rejects_expired_token():
    """Token forjado con exp en el pasado, firmado con el secreto correcto: lo
    único que lo invalida es la expiración."""
    user = seed_user("expired_uid", "expired_user")
    settings = get_settings()
    past = int(time.time()) - 60
    expired = jwt.encode(
        {"sub": user.user_id, "iat": past - 10, "exp": past},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_token"}


def test_me_rejects_token_signed_with_another_secret():
    user = seed_user("forged_uid", "forged_user")
    forged = jwt.encode(
        {"sub": user.user_id, "exp": int(time.time()) + 3600},
        "un-secreto-que-no-es-el-nuestro",
        algorithm="HS256",
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_token"}


def test_me_rejects_valid_token_of_deleted_user():
    """Token bien firmado pero cuyo sub ya no existe en el store."""
    response = client.get("/auth/me", headers=auth_headers("uid_que_no_existe"))
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_token"}


# --------------------------------------------------------------------------
# Los endpoints de perfil ahora piden token del dueño
# --------------------------------------------------------------------------

PROFILE_PAYLOAD = {
    "category": "test_categoria",
    "operating_days": ["mon"],
    "city": "Monterrey",
    "employees": "1",
    "answers": {"se_ha_quedado_sin_stock": True},
}


def test_profile_endpoints_require_a_token():
    assert client.post("/business-profile/test_auth_owner", json=PROFILE_PAYLOAD).status_code == 401
    assert client.get("/business-profile/test_auth_owner").status_code == 401


def test_profile_endpoints_reject_another_users_owner_id():
    seed_user("test_auth_owner", "auth_owner_a")
    seed_user("test_auth_intruso", "auth_owner_b")

    headers = auth_headers("test_auth_intruso")
    post = client.post("/business-profile/test_auth_owner", json=PROFILE_PAYLOAD, headers=headers)
    get = client.get("/business-profile/test_auth_owner", headers=headers)

    assert post.status_code == 403, post.text
    assert get.status_code == 403, get.text
    assert post.json() == {"detail": "forbidden_owner"}


def test_profile_endpoints_allow_own_owner_id():
    seed_user("test_auth_owner", "auth_owner_a")
    headers = auth_headers("test_auth_owner")

    assert client.post(
        "/business-profile/test_auth_owner", json=PROFILE_PAYLOAD, headers=headers
    ).status_code == 200
    assert client.get("/business-profile/test_auth_owner", headers=headers).status_code == 200


def test_category_stats_stays_public():
    """Solo agregados, cero PII: el dashboard comparativo lo consulta sin login."""
    assert client.get("/business-profile/stats/test_categoria").status_code == 200


# --------------------------------------------------------------------------
# Guard de esquema
# --------------------------------------------------------------------------

MIGRATION_USERS = Path(__file__).resolve().parents[1] / "sql" / "002_users.sql"


def test_snowflake_user_store_covers_all_stored_user_fields():
    """El INSERT y el SELECT de SnowflakeUserStore tienen que mencionar cada
    campo de StoredUser — incluido password_hash. No abre conexión."""
    expected = set(StoredUser.model_fields)

    selected = {c.strip() for c in snowflake_store.USER_COLUMNS.split(",")}
    assert selected == expected, f"columnas faltantes en el SELECT: {expected - selected}"

    insert_sql = inspect.getsource(snowflake_store.SnowflakeUserStore._create_user_sync)
    written = set(re.findall(r"%\((\w+)\)s", insert_sql))
    assert expected <= written, f"campos que el INSERT nunca escribe: {expected - written}"


def test_users_migration_declares_every_stored_user_column():
    """Si el schema crece y nadie toca la migración, la tabla real se queda
    corta y el INSERT truena hasta producción."""
    sql = MIGRATION_USERS.read_text(encoding="utf-8").lower()
    for field in StoredUser.model_fields:
        assert re.search(rf"\b{field}\b", sql), f"'{field}' no aparece en 002_users.sql"
    assert "create table if not exists" in sql, "la migración tiene que ser idempotente"
