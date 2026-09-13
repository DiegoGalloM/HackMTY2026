"""
Regresiones de la revisión de seguridad del registro/login.

Cada test de aquí corresponde a un hallazgo concreto. Si alguno empieza a
fallar, no es un detalle de estilo: es que volvió un agujero que ya se había
cerrado. El comentario de cada uno dice cuál.
"""

import asyncio
import inspect

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app
from app.models.schemas import BusinessProfile
from app.routers import auth as auth_router
from app.security import MIN_PASSWORD_LENGTH, validate_password
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

BASE_REGISTRATION = {
    "username": "hardening_base",
    "business_name": "Negocio",
    "full_name": "Persona Prueba",
    "birthdate": "1990-01-01",
    "password": "TortasRicas9x",
}


# --- Política de contraseñas -------------------------------------------------


def test_common_passwords_are_rejected():
    """La forma 'larga + mayúscula + minúscula + dígito' la cumplen justo las
    contraseñas más filtradas del mundo. Sin límite de intentos en /auth/login,
    la política es el único freno al adivinado en línea."""
    for weak in ("Password1234", "Contrasena123", "Qwerty123456", "Administrador1"):
        problems = validate_password(weak, "alguien")
        assert "too_common" in problems, f"{weak!r} debería rechazarse por común"


def test_password_minimum_is_at_least_twelve():
    """10 caracteres dejaban pasar casi todo el top-100. El mínimo no debe bajar."""
    assert MIN_PASSWORD_LENGTH >= 12
    assert "too_short" in validate_password("Abcdefgh123", "alguien")  # 11


def test_register_rejects_common_password_over_the_api():
    response = client.post(
        "/auth/register", json={**BASE_REGISTRATION, "password": "Password1234"}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "weak_password"
    assert "too_common" in response.json()["detail"]["problems"]


# --- Fuga de la contraseña en el 422 -----------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        [{**BASE_REGISTRATION}],  # array en vez de objeto
        {**BASE_REGISTRATION, "password": {"anidada": "SuperSecreta99x"}},
    ],
)
def test_validation_errors_never_echo_the_password(body):
    """El handler default de FastAPI mete el valor recibido en cada error, así
    que un body mal formado rebotaba la contraseña en claro. Los cuerpos 4xx son
    justo los que acaban en Sentry o en un HAR compartido."""
    response = client.post("/auth/register", json=body)
    assert response.status_code == 422
    assert "SuperSecreta99x" not in response.text
    assert "TortasRicas9x" not in response.text
    assert '"input"' not in response.text


# --- Configuración del JWT ---------------------------------------------------


def test_short_jwt_secret_is_refused_at_startup():
    """Un secreto corto se rompe offline y con él se firma un token para
    cualquier user_id. Mejor no arrancar que arrancar inseguro."""
    with pytest.raises(ValidationError):
        Settings(jwt_secret="corto123")


def test_jwt_algorithm_is_restricted_to_hmac():
    """jwt_algorithm viene del entorno y decode() confía en él."""
    with pytest.raises(ValidationError):
        Settings(jwt_secret="x" * 40, jwt_algorithm="none")
    with pytest.raises(ValidationError):
        Settings(jwt_secret="x" * 40, jwt_algorithm="RS256")


# --- bcrypt fuera del event loop ---------------------------------------------


def test_bcrypt_never_runs_on_the_event_loop():
    """register y login son `async def`: un bcrypt directo bloquea el loop y
    ~4 req/s bastan para congelar toda la API, sin cuenta y sin token."""
    for fn in (auth_router.register, auth_router.login):
        source = inspect.getsource(fn)
        for call in ("hash_password", "verify_password", "dummy_verify"):
            if call in source:
                assert f"asyncio.to_thread({call}" in source, (
                    f"{fn.__name__} llama {call} directo en el event loop"
                )


# --- Autorización estructural ------------------------------------------------


def test_owner_routes_are_guarded_by_the_router_not_by_each_endpoint():
    """La garantía tiene que ser estructural: una ruta nueva bajo
    /business-profile/{owner_id} debe nacer protegida."""
    from app.routers.business_profile import require_owner, router

    guards = [d.dependency for d in router.dependencies]
    assert require_owner in guards
    assert router.prefix.endswith("{owner_id}")


def test_owner_id_cannot_be_supplied_as_a_query_parameter():
    """Si owner_id se resolviera como query param, `?owner_id=<el mío>` pasaría
    el check mientras la ruta opera sobre el perfil de otro."""
    seed_user("victima_uid", "victima")
    seed_user("atacante_uid", "atacante")

    response = client.get(
        "/business-profile/victima_uid?owner_id=atacante_uid",
        headers=auth_headers("atacante_uid"),
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden_owner"}


# --- Topes de tamaño del perfil ----------------------------------------------


def test_profile_fields_are_bounded():
    """Sin topes, un usuario registrado podía mandar `answers` con miles de
    llaves y el endpoint PÚBLICO de stats se las servía a todo el mundo."""
    with pytest.raises(ValidationError):
        BusinessProfile(
            category="comida",
            operating_days=["mon"],
            city="Monterrey",
            answers={f"pregunta_{i}": True for i in range(5000)},
        )
    with pytest.raises(ValidationError):
        BusinessProfile(
            category="comida",
            operating_days=["mon"],
            city="Monterrey",
            answers={"a": True},
            week_description_audio_base64="A" * 3_000_000,
        )


# --- Unicidad en Snowflake ---------------------------------------------------


def test_snowflake_user_insert_uses_merge_for_locking():
    """INSERT ... WHERE NOT EXISTS no toma lock sobre la tabla destino: dos
    registros simultáneos del mismo username podían entrar los dos. MERGE sí
    serializa. No abre conexión a Snowflake, solo lee el SQL."""
    from app.storage.snowflake_store import SnowflakeUserStore

    # Se quitan las líneas de comentario antes de revisar: el comentario del
    # método explica justamente por qué ya NO se usa WHERE NOT EXISTS, y sin
    # esto el test se dispararía con su propia explicación.
    source = inspect.getsource(SnowflakeUserStore._create_user_sync)
    sql = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )
    assert "MERGE INTO users" in sql
    assert "WHERE NOT EXISTS" not in sql

    lookup = inspect.getsource(SnowflakeUserStore._get_user_by_username_sync)
    assert "ORDER BY created_at" in lookup and "LIMIT 1" in lookup


def test_memory_user_store_rejects_duplicates_case_insensitively():
    from app.models.schemas import StoredUser
    from app.storage.memory_store import MemoryUserStore

    store = MemoryUserStore()
    base = {
        "business_name": "N",
        "full_name": "P",
        "birthdate": "1990-01-01",
        "password_hash": "x",
    }
    assert asyncio.run(store.create_user(StoredUser(user_id="1", username="tienda", **base))) is True
    assert asyncio.run(store.create_user(StoredUser(user_id="2", username="TIENDA", **base))) is False
