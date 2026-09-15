"""
Fase 6 del roadmap: visibilidad básica de errores.

  - Un error no controlado responde 500 con `error_id` y sin detalles internos.
  - Con SENTRY_DSN el error llega a Sentry SIN datos sensibles (probado con un
    transporte en memoria, en un subproceso: nada sale a internet).
  - /health/ready revisa base, Nessie y LLM, y distingue caído de degradado.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import observability
from app.config import Settings
from app.main import app
from app.nessie.base import NessieClient
from app.routers import health

client = TestClient(app)
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _fresh_health_cache():
    health.reset_cache()
    yield
    health.reset_cache()


# --- Errores no controlados --------------------------------------------------


def _boom_app() -> FastAPI:
    boom = FastAPI()
    boom.add_exception_handler(Exception, observability.unhandled_exception_handler)

    @boom.get("/explota")
    async def explota():
        raise RuntimeError("detalle interno que no debe salir: /srv/app/secreto.py")

    return boom


def test_the_real_app_uses_the_unhandled_exception_handler():
    assert app.exception_handlers[Exception] is observability.unhandled_exception_handler


def test_unhandled_error_returns_500_with_error_id_and_no_internals(caplog):
    response = TestClient(_boom_app(), raise_server_exceptions=False).get("/explota")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "internal_error"
    assert len(body["error_id"]) == 12
    assert "secreto" not in response.text and "Traceback" not in response.text
    # El mismo id queda en el log, con la traza, para buscarlo en Render.
    assert any(body["error_id"] in record.getMessage() for record in caplog.records)


def test_without_dsn_sentry_stays_off():
    assert observability.init_error_tracking(Settings(jwt_secret="x" * 40, sentry_dsn="", _env_file=None)) is False
    assert observability.error_tracking_mode() == "logs"


def test_sentry_events_never_carry_secrets():
    secrets = {
        "PROBE_TOKEN": "tok_" + "pruebasecreta0123456789",
        "PROBE_KEY": "nessie" + "keysecreta",
        "PROBE_PASSWORD": "Contra" + "senaSecreta99",
        "PROBE_AUDIO": "UklGR" + "hoAAABXQVZF",
        "PROBE_JWT": "jwt" + "secretisimo",
    }
    env = {**os.environ, **secrets, "PYTHONPATH": str(BACKEND_DIR), "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run(
        [sys.executable, "-m", "tests.sentry_capture_probe"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
    )
    assert run.returncode == 0, run.stderr[-2000:]
    result = json.loads(run.stdout)

    assert result["enabled"] is True
    assert [r["status"] for r in result["responses"]] == [500, 500]
    error_ids = [r["body"]["error_id"] for r in result["responses"]]
    assert len(set(error_ids)) == 2, "cada error debe tener su propio id"
    # Un evento por error, y el id que ve el cliente es el event_id de Sentry.
    assert len(result["events"]) == 2
    assert sorted(e["event_id"][:12] for e in result["events"]) == sorted(error_ids)

    dump = json.dumps(result["events"])
    for name, value in secrets.items():
        assert value not in dump, f"{name} se filtró a Sentry"
    for event in result["events"]:
        assert event["request"]["url"].endswith("/pay/[token]")
        assert "authorization" not in {h.lower() for h in event["request"].get("headers", {})}
        frames = [f for v in event["exception"]["values"] for f in v["stacktrace"]["frames"]]
        assert all("vars" not in f for f in frames)


def test_scrub_event_cleans_every_known_leak():
    event = {
        "request": {
            "url": "https://api.example.com/pay/tok_abc123",
            "data": {"password": "x"},
            "cookies": {"s": "1"},
            "query_string": "key=abc",
            "headers": {"Authorization": "Bearer t", "Cookie": "s=1", "User-Agent": "ua"},
        },
        "transaction": "/pay/tok_abc123",
        "user": {"ip_address": "1.2.3.4"},
        "logentry": {"message": "GET http://api.nessieisreal.com/x?key=abc"},
        "exception": {"values": [{"value": "for url 'http://h/x?key=abc'", "stacktrace": {"frames": [{"vars": {"token": "t"}}]}}]},
        "breadcrumbs": {"values": [{"message": "GET /pay/tok_abc123", "data": {"url": "http://h/pay/tok_abc123?key=abc"}}]},
    }
    clean = json.dumps(observability.scrub_event(event))
    for leak in ("tok_abc123", "key=abc", "password", "Bearer t", "1.2.3.4", '"vars"', "s=1"):
        assert leak not in clean, leak
    assert "User-Agent" in clean


# --- /health y /health/ready -------------------------------------------------


def test_liveness_stays_fast_and_dependency_free():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["error_tracking"] == "logs"


def test_readiness_in_mock_mode_reports_every_dependency():
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    checks = body["checks"]
    assert checks["database"]["status"] == "ok" and checks["database"]["mode"] == "sqlite"
    assert checks["nessie"] == {**checks["nessie"], "status": "ok", "mode": "mock"}
    assert checks["llm"] == {**checks["llm"], "status": "ok", "mode": "none"}
    assert all(isinstance(c["latency_ms"], int) for c in checks.values())


def test_database_down_is_503(monkeypatch):
    def broken_db():
        raise RuntimeError("no se pudo conectar a Snowflake")

    monkeypatch.setattr(health, "get_db", broken_db)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "down"
    assert response.json()["checks"]["database"]["status"] == "down"


class _BrokenNessie(NessieClient):
    async def list_customers(self):
        request = httpx.Request("GET", "http://api.nessieisreal.com/customers?key=llave_secreta_nessie")
        raise httpx.HTTPStatusError(
            "Client error '401 Unauthorized' for url 'http://api.nessieisreal.com/customers?key=llave_secreta_nessie'",
            request=request, response=httpx.Response(401, request=request),
        )

    async def list_accounts(self, customer_id):  # pragma: no cover - no se usa
        return []

    async def get_account(self, account_id):  # pragma: no cover
        return {}

    async def list_transactions(self, account_id):  # pragma: no cover
        return []

    async def create_purchase(self, *args, **kwargs):  # pragma: no cover
        return {}


def test_real_nessie_down_is_degraded_and_never_leaks_the_key(monkeypatch):
    monkeypatch.setattr(health, "get_nessie_client", lambda: _BrokenNessie())
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["nessie"]["status"] == "down"
    assert "llave_secreta_nessie" not in response.text


def test_invalid_anthropic_key_is_degraded(monkeypatch):
    monkeypatch.setattr(health, "build_llm", lambda settings, db: type("FakeLLM", (), {"name": "anthropic"})())

    async def rejected(api_key):
        raise RuntimeError("401 invalid x-api-key")

    monkeypatch.setattr(health, "_anthropic_reachable", rejected)
    body = client.get("/health/ready").json()
    assert body["status"] == "degraded"
    assert body["checks"]["llm"]["status"] == "down"


def test_a_hanging_dependency_times_out_instead_of_hanging_the_endpoint(monkeypatch):
    async def hangs():
        await asyncio.sleep(10)

    monkeypatch.setattr(health, "CHECK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(health, "check_nessie", hangs)
    body = client.get("/health/ready").json()
    assert body["checks"]["nessie"]["status"] == "down"
    assert "sin respuesta" in body["checks"]["nessie"]["detail"]


def test_readiness_is_cached_so_monitors_do_not_hammer_dependencies(monkeypatch):
    calls = {"n": 0}
    original = health.check_database

    async def counted():
        calls["n"] += 1
        return await original()

    monkeypatch.setattr(health, "check_database", counted)
    for _ in range(3):
        assert client.get("/health/ready").status_code == 200
    assert calls["n"] == 1


def test_logging_stays_quiet_about_healthy_checks(caplog):
    with caplog.at_level(logging.ERROR):
        client.get("/health/ready")
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
