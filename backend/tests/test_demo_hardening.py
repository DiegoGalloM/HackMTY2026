"""
Fase 5 del roadmap: costuras de datos y seguridad de un demo público.

Cada bloque corresponde a un punto de docs/ROADMAP_PULIDO.md §5:
  - el audio de la encuesta no vive en la fila del perfil y caduca;
  - JWT_SECRET es obligatorio en producción;
  - las rutas públicas tienen límite de peticiones por IP.
"""

import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import ratelimit
from app.config import Settings
from app.main import app
from app.models.schemas import BusinessProfile
from app.ratelimit import LIMITS, SlidingWindowLimiter
from app.storage import audio_store, get_store
from app.storage.audio_store import OnboardingAudioStore
from scripts import purge_legacy_profile_audio
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

PROFILE = {
    "category": "hardening_categoria",
    "operating_days": ["mon"],
    "city": "Monterrey",
    "employees": "1",
    "answers": {"guarda_inventario": True},
    "week_description_mode": "audio",
    "week_description_text": None,
    "week_description_audio_base64": "UklGRhoAAABXQVZF",
    "week_description_audio_mime": "audio/webm",
}


def _audio_rows(db, owner_id):
    return db.rows("SELECT * FROM onboarding_audio WHERE owner_id = :o", {"o": owner_id})


# --- Audio de la encuesta ----------------------------------------------------


def test_audio_goes_to_its_own_table_with_expiry_and_never_to_the_profile_row(db):
    owner = "hardening_audio_1"
    seed_user(owner, "hardening_audio_1")
    headers = auth_headers(owner)

    assert client.post(f"/business-profile/{owner}", json=PROFILE, headers=headers).status_code == 200

    # En el store de perfiles (la fila) no hay voz.
    stored = app.dependency_overrides[get_store]()._profiles[owner]
    assert stored.week_description_audio_base64 is None
    assert stored.week_description_audio_mime is None
    # Vive aparte, con fecha de caducidad a los días de retención.
    rows = _audio_rows(db, owner)
    assert len(rows) == 1 and rows[0]["audio_base64"] == PROFILE["week_description_audio_base64"]
    expires = datetime.fromisoformat(str(rows[0]["expires_at"]))
    expected = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=Settings(jwt_secret="x" * 40).onboarding_audio_retention_days)
    assert abs(expires - expected) < timedelta(minutes=5)
    # Y no vuelve a salir por la API.
    saved = client.get(f"/business-profile/{owner}", headers=headers).json()
    assert saved["week_description_audio_base64"] is None


def test_redoing_the_survey_in_text_mode_deletes_the_previous_voice(db):
    owner = "hardening_audio_2"
    seed_user(owner, "hardening_audio_2")
    headers = auth_headers(owner)
    client.post(f"/business-profile/{owner}", json=PROFILE, headers=headers)
    assert _audio_rows(db, owner)

    text_mode = {**PROFILE, "week_description_mode": "text", "week_description_text": "Vendo más los sábados.",
                 "week_description_audio_base64": None, "week_description_audio_mime": None}
    client.post(f"/business-profile/{owner}", json=text_mode, headers=headers)
    assert _audio_rows(db, owner) == []


def test_zero_retention_never_stores_audio(db):
    store = OnboardingAudioStore(db, retention_days=0)
    assert store.save("hardening_audio_3", "UklGRg==", "audio/webm") is False
    assert _audio_rows(db, "hardening_audio_3") == []


def test_expired_audio_is_hidden_and_purged(db):
    store = OnboardingAudioStore(db, retention_days=7)
    past = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)).isoformat()
    db.execute(
        "INSERT INTO onboarding_audio (owner_id, audio_base64, audio_mime, created_at, expires_at) "
        "VALUES ('hardening_audio_old', 'UklGRg==', 'audio/webm', :t, :t)",
        {"t": past},
    )
    store.save("hardening_audio_new", "UklGRg==", "audio/webm")

    assert store.get("hardening_audio_old") is None
    assert store.get("hardening_audio_new") is not None
    store.purge_expired()
    assert _audio_rows(db, "hardening_audio_old") == []
    assert len(_audio_rows(db, "hardening_audio_new")) == 1


def test_purge_is_throttled_per_process(db, monkeypatch):
    monkeypatch.setattr(audio_store, "_last_purge", {})
    store = OnboardingAudioStore(db, retention_days=7)
    assert store.maybe_purge_expired() is True
    assert store.maybe_purge_expired() is False  # dentro del intervalo no vuelve a purgar


def test_get_profile_never_returns_legacy_audio_left_in_the_row():
    """Perfiles guardados antes de la Fase 5 pueden traer audio en la fila."""
    owner = "hardening_legacy"
    seed_user(owner, "hardening_legacy")
    legacy = BusinessProfile(**PROFILE)
    app.dependency_overrides[get_store]()._profiles[owner] = legacy

    saved = client.get(f"/business-profile/{owner}", headers=auth_headers(owner)).json()
    assert saved["week_description_audio_base64"] is None
    assert saved["week_description_audio_mime"] is None


def test_automatic_migrations_never_destroy_profile_data():
    """Las migraciones de backend/sql/ se aplican solas al arrancar con
    USE_SNOWFLAKE=true (y Render despliega en cada push). Borrar el audio viejo
    es un paso manual de la Fase 9, nunca una migración automática."""
    sql_dir = Path(__file__).resolve().parents[1] / "sql"
    for path in sql_dir.glob("*.sql"):
        code = "\n".join(line.split("--")[0] for line in path.read_text(encoding="utf-8").splitlines()).upper()
        for destructive in ("DROP ", "DELETE ", "UPDATE ", "TRUNCATE "):
            assert destructive not in code, f"{path.name} contiene {destructive.strip()}"


class _FakeCursor:
    def __init__(self, pending):
        self.pending = pending
        self.statements = []

    def execute(self, sql):
        self.statements.append(sql)

    def fetchone(self):
        return (self.pending,)


class _FakeConn:
    def __init__(self, pending):
        self.cur = _FakeCursor(pending)

    def cursor(self):
        return self.cur


def test_legacy_audio_purge_is_a_dry_run_unless_applied():
    conn = _FakeConn(pending=3)
    assert purge_legacy_profile_audio.purge(conn, apply=False, log_fn=lambda _m: None) == 3
    assert not any(s.startswith("UPDATE") for s in conn.cur.statements)

    conn = _FakeConn(pending=3)
    purge_legacy_profile_audio.purge(conn, apply=True, log_fn=lambda _m: None)
    assert any(s.startswith("UPDATE business_profiles SET week_description_audio_base64 = NULL") for s in conn.cur.statements)


# --- JWT_SECRET en producción ------------------------------------------------


def test_production_refuses_to_start_without_jwt_secret():
    """Un secreto efímero en producción cierra la sesión de todos en cada deploy."""
    with pytest.raises(ValidationError, match="JWT_SECRET es obligatorio"):
        Settings(environment="production", jwt_secret="", _env_file=None)


def test_production_with_a_secret_and_development_without_one_both_start():
    assert Settings(environment="production", jwt_secret="s" * 48, _env_file=None).is_production
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        dev = Settings(environment="development", jwt_secret="", _env_file=None)
    assert len(dev.jwt_secret) >= 32


# --- Rate limiting en rutas públicas -----------------------------------------


PUBLIC_ROUTES = {
    ("GET", "/pay/{token}"): "pay",
    ("POST", "/pay/{token}"): "pay",
    ("GET", "/business-profile/stats/{category}"): "stats",
    ("POST", "/demo/session"): "demo_session",
    ("POST", "/auth/register"): "auth_register",
    ("POST", "/auth/login"): "auth_login",
}


def test_every_public_route_has_a_rate_limit():
    """Guard estructural: si alguien quita el límite de una ruta pública, truena."""
    found = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        buckets = {getattr(d.dependency, "rate_limit_bucket", None) for d in route.dependencies} - {None}
        for method in route.methods:
            if (method, route.path) in PUBLIC_ROUTES:
                found[(method, route.path)] = buckets
    for key, bucket in PUBLIC_ROUTES.items():
        assert found.get(key) == {bucket}, f"{key} sin rate limit '{bucket}' (tiene {found.get(key)})"


def test_pay_route_answers_429_with_retry_after_once_the_window_is_full():
    token = "tok_inexistente_para_el_limite_0123456789"
    for _ in range(LIMITS["pay"]):
        assert client.get(f"/pay/{token}").status_code == 404
    blocked = client.get(f"/pay/{token}")
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "rate_limited"}
    assert int(blocked.headers["Retry-After"]) >= 1


def test_the_frontend_can_read_retry_after_across_origins():
    """El frontend desplegado vive en otro origen: si CORS no expone
    Retry-After, el navegador lo esconde y la app no puede decir cuánto esperar."""
    origin = {"Origin": "http://localhost:5173"}
    response = None
    for _ in range(LIMITS["stats"] + 1):
        response = client.get("/business-profile/stats/limite_cors", headers=origin)
    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()


def test_stats_route_is_limited_too():
    for _ in range(LIMITS["stats"]):
        assert client.get("/business-profile/stats/limite_test").status_code == 200
    assert client.get("/business-profile/stats/limite_test").status_code == 429


def test_login_is_limited_against_online_guessing():
    body = {"username": "nadie_existe", "password": "NoEsLaBuena123"}
    for _ in range(LIMITS["auth_login"]):
        assert client.post("/auth/login", json=body).status_code == 401
    assert client.post("/auth/login", json=body).status_code == 429


def test_rate_limit_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(ratelimit, "get_settings", lambda: SimpleNamespace(rate_limit_enabled=False, trust_proxy_headers=False))
    for _ in range(LIMITS["stats"] + 5):
        assert client.get("/business-profile/stats/limite_apagado").status_code == 200


def test_each_ip_has_its_own_window():
    limiter = SlidingWindowLimiter()
    assert all(limiter.hit("b", "1.1.1.1", 2) is None for _ in range(2))
    assert limiter.hit("b", "1.1.1.1", 2) is not None
    assert limiter.hit("b", "2.2.2.2", 2) is None


def test_behind_a_trusted_proxy_the_last_forwarded_hop_is_the_client(monkeypatch):
    """El proxy agrega al final la IP que vio; lo de antes lo escribe el cliente
    y usarlo permitiría saltarse el límite cambiando el header."""
    request = SimpleNamespace(headers={"x-forwarded-for": "6.6.6.6, 203.0.113.7"}, client=SimpleNamespace(host="10.0.0.1"))
    monkeypatch.setattr(ratelimit, "get_settings", lambda: SimpleNamespace(trust_proxy_headers=True))
    assert ratelimit.client_ip(request) == "203.0.113.7"
    monkeypatch.setattr(ratelimit, "get_settings", lambda: SimpleNamespace(trust_proxy_headers=False))
    assert ratelimit.client_ip(request) == "10.0.0.1"
