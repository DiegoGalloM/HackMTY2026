"""
Checklist OWASP API Security Top 10 (2023), en tests (Fase 7 del roadmap).

Cada bloque dice qué riesgo cubre. Lo que ya estaba cubierto en otro archivo
se referencia en docs/SECURITY_CHECKLIST.md en vez de repetirse aquí.
"""

import base64
import json
import re
import time

import jwt
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import http_hardening
from app.config import Settings, get_settings
from app.main import app
from app.nessie import get_nessie_client
from app.nessie.mock_client import MockNessieClient
from app.routers.auth import get_current_user
from app.security import create_access_token
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

OWNER = "owasp_owner"
OTHER = "owasp_other"


def setup_module(module):
    seed_user(OWNER, "owasp_owner_user", business_name="Negocio OWASP")
    seed_user(OTHER, "owasp_other_user")
    client.post(
        f"/business-profile/{OWNER}",
        json={"category": "comida", "operating_days": ["mon"], "city": "Austin", "employees": "1", "answers": {}},
        headers=auth_headers(OWNER),
    )


def _new_order(price: float = 25) -> dict:
    h = auth_headers(OWNER)
    flour = client.post(f"/business/{OWNER}/inventory", json={"name": f"Harina {time.time_ns()}", "unit_of_measure": "kg", "initial_quantity": 100, "initial_unit_cost": 1.0}, headers=h).json()
    item = client.post(
        f"/business/{OWNER}/catalog",
        json={"name": f"Pan {time.time_ns()}", "item_type": "PRODUCT", "selling_price": price, "tax_rate": 0, "components": [{"inventory_item_id": flour["inventory_item_id"], "quantity_per_unit": 1}]},
        headers=h,
    ).json()
    order = client.post(f"/business/{OWNER}/orders", json={"lines": [{"item_id": item["item_id"], "quantity": 1}]}, headers=h)
    assert order.status_code == 201, order.text
    return order.json()


# --- API1 · Broken Object Level Authorization --------------------------------


def test_api1_another_owner_cannot_write_into_my_business(db):
    before = db.scalar("SELECT COUNT(*) FROM sales_orders WHERE business_id = :b", {"b": OWNER})
    response = client.post(f"/business/{OWNER}/orders", json={"lines": [{"item_id": "x", "quantity": 1}]}, headers=auth_headers(OTHER))
    assert response.status_code == 403
    assert db.scalar("SELECT COUNT(*) FROM sales_orders WHERE business_id = :b", {"b": OWNER}) == before
    ask = client.post(f"/business/{OWNER}/assistant/ask", json={"question": "¿Cómo van mis ventas?"}, headers=auth_headers(OTHER))
    assert ask.status_code == 403


# --- API2 · Broken Authentication --------------------------------------------


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


@pytest.mark.parametrize(
    "forge",
    [
        pytest.param(lambda token: jwt.encode({"sub": OWNER, "exp": int(time.time()) + 600}, None, algorithm="none"), id="alg-none"),
        pytest.param(lambda token: ".".join([token.split(".")[0], _b64({"sub": OWNER, "exp": int(time.time()) + 600}), token.split(".")[2]]), id="payload-cambiado"),
        pytest.param(lambda token: token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB"), id="firma-alterada"),
        pytest.param(lambda token: jwt.encode({"sub": OWNER}, get_settings().jwt_secret, algorithm="HS256"), id="sin-exp"),
    ],
)
def test_api2_forged_tokens_are_rejected(forge):
    other_token, _ = create_access_token(OTHER)
    forged = forge(other_token)
    for path in ("/auth/me", f"/business/{OWNER}/overview"):
        assert client.get(path, headers={"Authorization": f"Bearer {forged}"}).status_code == 401, path


# --- API3 · Broken Object Property Level Authorization (mass assignment) -----


def test_api3_register_ignores_fields_the_client_must_not_set():
    body = {
        "username": "masivo_owasp", "business_name": "Negocio", "full_name": "Persona Prueba", "birthdate": "1990-01-01",
        "password": "TortasRicas9x", "user_id": "admin", "password_hash": "$2b$12$falso", "is_admin": True,
    }
    response = client.post("/auth/register", json=body)
    assert response.status_code == 201, response.text
    user = response.json()["user"]
    assert user["user_id"] != "admin"
    assert "password_hash" not in user and "is_admin" not in user
    assert client.post("/auth/login", json={"username": "masivo_owasp", "password": "TortasRicas9x"}).status_code == 200


def test_api3_the_customer_cannot_change_status_or_amount_of_an_order():
    order = _new_order(price=25)
    tricky = {"card_last4": "4242", "status": "PAID", "total": 0.01, "amount": 0.01, "subtotal": 0}
    paid = client.post(f"/pay/{order['checkout_token']}", json=tricky)
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "PAID"
    assert paid.json()["total"] == order["total"] == 25


# --- API4 · Unrestricted Resource Consumption --------------------------------


def test_api4_oversized_bodies_are_rejected_before_reaching_the_route(user_store):
    limit = get_settings().max_request_body_bytes
    huge = json.dumps({"username": "enorme_owasp", "password": "x" * (limit + 10), "business_name": "N", "full_name": "P P", "birthdate": "1990-01-01"})
    response = client.post("/auth/register", content=huge, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json() == {"detail": "payload_too_large"}


def test_api4_oversized_chunked_bodies_without_content_length_are_rejected_too():
    limit = get_settings().max_request_body_bytes

    def chunks():
        for _ in range((limit // 65536) + 2):
            yield b"x" * 65536

    response = client.post("/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_api4_normal_bodies_still_pass():
    assert client.post("/auth/login", json={"username": "nadie_owasp", "password": "NoEsLaBuena123"}).status_code == 401


def test_api4_list_sizes_and_question_length_are_bounded():
    h = auth_headers(OWNER)
    assert client.get(f"/business/{OWNER}/orders?limit=100000", headers=h).status_code == 422
    assert client.post(f"/business/{OWNER}/assistant/ask", json={"question": "a" * 501}, headers=h).status_code == 422


# --- API5 · Broken Function Level Authorization ------------------------------

# Las únicas rutas que se pueden llamar sin token. Todas las públicas con
# trabajo real tienen rate limit (tests/test_demo_hardening.py).
PUBLIC_ROUTES = {
    ("GET", "/health"), ("GET", "/health/ready"),
    ("POST", "/auth/register"), ("POST", "/auth/login"),
    ("GET", "/demo/businesses"), ("POST", "/demo/session"),
    ("GET", "/pay/{token}"), ("POST", "/pay/{token}"),
    ("GET", "/business-profile/stats/{category}"),
}


def _dependency_calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _dependency_calls(dep)


def test_api5_every_non_public_route_requires_a_token():
    """Guard estructural: una ruta nueva sin autenticación rompe CI."""
    unguarded = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        calls = set(_dependency_calls(route.dependant))
        for method in route.methods:
            if (method, route.path) in PUBLIC_ROUTES:
                continue
            if http_hardening.require_legacy_nessie_routes in calls:
                assert route.path.startswith("/accounts"), route.path
                continue
            if get_current_user not in calls:
                unguarded.append(f"{method} {route.path}")
    assert unguarded == []


# --- API6 · Unrestricted Access to Sensitive Business Flows ------------------
# Pagar dos veces la misma orden no duplica asientos ni inventario:
# tests/test_finance_api.py::test_full_qr_sale_flow_reaches_books_analytics_and_assistant.


# --- API7 · Server Side Request Forgery --------------------------------------

_URLISH = re.compile(r"url|uri|callback|webhook|redirect|endpoint|host", re.IGNORECASE)


def _model_fields(model: type[BaseModel], prefix: str = ""):
    for name, field in model.model_fields.items():
        yield f"{prefix}{name}"
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            yield from _model_fields(annotation, f"{prefix}{name}.")


def test_api7_no_endpoint_accepts_a_url_to_fetch():
    """El backend nunca descarga una URL que mande el cliente: no hay campo que la reciba."""
    suspicious = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        names = [p.name for p in route.dependant.query_params + route.dependant.path_params]
        for body in route.dependant.body_params:
            if isinstance(body.type_, type) and issubclass(body.type_, BaseModel):
                names.extend(_model_fields(body.type_))
            else:
                names.append(body.name)
        suspicious += [f"{route.path}: {n}" for n in names if _URLISH.search(n)]
    assert suspicious == []


# --- API8 · Security Misconfiguration (incluye inyección) --------------------


class _ExplodingNessie(MockNessieClient):
    async def list_accounts(self, customer_id):
        raise RuntimeError("fallo interno en /srv/app/secreto.py con key=abc123")


def test_api8_a_real_route_that_crashes_leaks_no_internals():
    app.dependency_overrides[get_nessie_client] = lambda: _ExplodingNessie()
    try:
        response = TestClient(app, raise_server_exceptions=False).get("/accounts/customer/cust_1")
    finally:
        app.dependency_overrides.pop(get_nessie_client, None)
    assert response.status_code == 500
    assert response.json()["detail"] == "internal_error"
    for leak in ("secreto.py", "abc123", "Traceback", "RuntimeError"):
        assert leak not in response.text


def test_api8_security_headers_are_on_every_response():
    for response in (client.get("/health"), client.get("/no-existe"), client.post("/auth/login", content=b"x" * (get_settings().max_request_body_bytes + 1))):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"


def test_api8_cors_only_answers_configured_origins_and_never_with_credentials():
    evil = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers
    allowed_origin = get_settings().cors_origin_list[0]
    ok = client.get("/health", headers={"Origin": allowed_origin})
    assert ok.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-credentials" not in ok.headers


@pytest.mark.parametrize("payload", ["' OR '1'='1", "x'; DROP TABLE sales_orders; --", "\" OR 1=1 --", "%' UNION SELECT * FROM users --"])
def test_api8_sql_injection_attempts_are_plain_data(db, payload):
    h = auth_headers(OWNER)
    orders_before = db.scalar("SELECT COUNT(*) FROM sales_orders")
    accounts_before = db.scalar("SELECT COUNT(*) FROM accounts")

    stats = client.get(f"/business-profile/stats/{payload}")
    assert stats.status_code == 200 and stats.json()["n_negocios"] == 0
    filtered = client.get(f"/business/{OWNER}/orders", params={"status": payload}, headers=h)
    assert filtered.status_code == 200 and filtered.json() == []
    assert client.get(f"/business/{payload}/overview", headers=h).status_code == 403
    assert client.get(f"/pay/{payload}{'x' * 20}").status_code == 404
    created = client.post(f"/business/{OWNER}/inventory", json={"name": payload, "unit_of_measure": "kg", "initial_quantity": 1, "initial_unit_cost": 1}, headers=h)
    assert created.status_code == 201 and created.json()["name"] == payload

    assert db.scalar("SELECT COUNT(*) FROM sales_orders") == orders_before
    assert db.scalar("SELECT COUNT(*) FROM accounts") == accounts_before


# --- API9 · Improper Inventory Management ------------------------------------


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(environment="production", jwt_secret="x" * 40, _env_file=None), 404),
        (Settings(environment="development", jwt_secret="x" * 40, _env_file=None), 200),
        (Settings(environment="production", enable_legacy_nessie_routes=True, jwt_secret="x" * 40, _env_file=None), 200),
    ],
    ids=["produccion-apagadas", "desarrollo-encendidas", "produccion-forzadas"],
)
def test_api9_legacy_nessie_routes_are_off_in_production(monkeypatch, settings, expected):
    monkeypatch.setattr(http_hardening, "get_settings", lambda: settings)
    assert client.get("/accounts/customer/cust_1").status_code == expected
    simulate = client.post("/accounts/acc_1/transactions/simulate", json={"merchant_id": "m", "amount": 1.0})
    assert simulate.status_code == expected


def test_api9_legacy_purchase_simulation_is_bounded():
    assert client.post("/accounts/acc_1/transactions/simulate", json={"merchant_id": "m", "amount": -5}).status_code == 422
    assert client.post("/accounts/acc_1/transactions/simulate", json={"merchant_id": "m" * 100, "amount": 1}).status_code == 422


# --- API10 · Unsafe Consumption of APIs --------------------------------------
# - Lo que redacta el LLM pasa por la guardia de cifras:
#   tests/test_assistant_golden.py (batería de LLM tramposo sobre 45 preguntas).
# - Los errores de Nessie real no filtran su key:
#   tests/test_error_visibility.py::test_real_nessie_down_is_degraded_and_never_leaks_the_key.
