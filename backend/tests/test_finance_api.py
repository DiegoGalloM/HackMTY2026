"""
Flujo principal por HTTP: catálogo -> orden -> QR (token) -> pago del cliente
-> libros, análisis y asistente reflejan la venta. Y la guardia de tenant.
"""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

OWNER = "fin_owner"
INTRUDER = "fin_intruder"


def setup_module(module):
    seed_user(OWNER, "fin_owner_user", business_name="Pastelería Prueba")
    seed_user(INTRUDER, "fin_intruder_user")
    client.post(
        f"/business-profile/{OWNER}",
        json={"category": "comida", "operating_days": ["mon"], "city": "Austin", "employees": "1", "answers": {"guarda_inventario": True}},
        headers=auth_headers(OWNER),
    )


def _h():
    return auth_headers(OWNER)


def test_onboarding_initialised_chart_of_accounts():
    accounts = client.get(f"/business/{OWNER}/books/accounts", headers=_h()).json()
    assert any(a["account_number"] == 1200 for a in accounts)
    assert any(a["account_subtype"] == "PACKAGING" for a in accounts)  # extra de "comida"


def test_full_qr_sale_flow_reaches_books_analytics_and_assistant():
    h = _h()
    flour = client.post(f"/business/{OWNER}/inventory", json={"name": "Harina", "unit_of_measure": "kg", "initial_quantity": 10, "initial_unit_cost": 1.0, "reorder_point": 2}, headers=h)
    assert flour.status_code == 201, flour.text
    flour = flour.json()
    cake = client.post(
        f"/business/{OWNER}/catalog",
        json={"name": "Pastel", "item_type": "PRODUCT", "selling_price": 25, "tax_rate": 0.08, "components": [{"inventory_item_id": flour["inventory_item_id"], "quantity_per_unit": 0.5}]},
        headers=h,
    )
    assert cake.status_code == 201, cake.text
    cake = cake.json()
    assert cake["producible_units"] == 20 and cake["estimated_unit_cost"] == 0.5

    order = client.post(f"/business/{OWNER}/orders", json={"lines": [{"item_id": cake["item_id"], "quantity": 2}]}, headers=h)
    assert order.status_code == 201, order.text
    order = order.json()
    assert order["status"] == "AWAITING_PAYMENT" and order["total"] == 54
    token = order["checkout_token"]

    # El cliente abre el checkout sin sesión: ve qué compra, no lo edita.
    page = client.get(f"/pay/{token}")
    assert page.status_code == 200
    assert page.json()["business_name"] == "Pastelería Prueba"
    assert page.json()["total"] == 54 and page.json()["lines"][0]["item_name"] == "Pastel"
    assert client.get("/pay/no-such-token-xxxxxxxxxxxxxxxxxxxxx").status_code == 404
    # Abrir el checkout NO mueve inventario.
    assert client.get(f"/business/{OWNER}/inventory", headers=h).json()["items"][0]["quantity_on_hand"] == 10

    paid = client.post(f"/pay/{token}", json={"card_last4": "4242", "customer_name": "Ana", "customer_email": "ana@example.com"})
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "PAID" and paid.json()["payment"]["card_last4"] == "4242"
    # Reintento del cliente: mismo recibo, sin doble cobro.
    again = client.post(f"/pay/{token}", json={})
    assert again.status_code == 200 and again.json()["already_paid"] is True

    inventory = client.get(f"/business/{OWNER}/inventory", headers=h).json()
    assert inventory["items"][0]["quantity_on_hand"] == 9
    journal = client.get(f"/business/{OWNER}/books/journal", headers=h).json()
    assert {e["source_type"] for e in journal} >= {"SALE_COMPLETED", "SALE_COGS", "OWNER_CONTRIBUTION"}
    assert len([e for e in journal if e["source_type"] == "SALE_COMPLETED"]) == 1
    tb = client.get(f"/business/{OWNER}/books/trial-balance", headers=h).json()
    assert tb["balanced"] is True
    bs = client.get(f"/business/{OWNER}/books/balance-sheet", headers=h).json()
    assert bs["balanced"] is True
    inc = client.get(f"/business/{OWNER}/books/income-statement?period=all", headers=h).json()
    assert inc["total_revenue"] == 50 and inc["total_cogs"] == 1.0
    health = client.get(f"/business/{OWNER}/analytics/health?period=month", headers=h).json()
    assert health["revenue"]["value"] == 50 and health["integrity"]["trial_balance_balanced"]
    ratios = client.get(f"/business/{OWNER}/analytics/ratios", headers=h).json()
    assert any(r["key"] == "gross_margin" and r["available"] for r in ratios["ratios"])
    customers = client.get(f"/business/{OWNER}/customers", headers=h).json()
    assert customers[0]["display_name"] == "Ana" and customers[0]["purchase_count"] == 1

    answer = client.post(f"/business/{OWNER}/assistant/ask", json={"question": "¿Cuánto vendí este mes?"}, headers=h).json()
    assert answer["intent"] == "sales" and "$50.00" in answer["answer"]
    assert any(e["value"] == "$50.00" for e in answer["evidence"])


def test_card_purchase_review_flow_over_http():
    h = _h()
    tx = client.post(f"/business/{OWNER}/purchases/simulate", json={"scenario": 1}, headers=h)  # Amazon
    assert tx.status_code == 201, tx.text
    tx = tx.json()
    assert tx["needs_review"] is True
    suggestion = client.get(f"/business/{OWNER}/purchases/{tx['transaction_id']}/suggestion", headers=h).json()
    assert suggestion["requires_user_confirmation"] is True
    fixed = client.post(f"/business/{OWNER}/purchases/{tx['transaction_id']}/classify", json={"kind": "EQUIPMENT"}, headers=h).json()
    assert fixed["classification_status"] == "CLASSIFIED" and fixed["kind_label"] == "Equipo o herramienta"
    rd = client.post(f"/business/{OWNER}/purchases/simulate", json={"scenario": 0}, headers=h).json()  # Restaurant Depot
    assert rd["sample_receipt_available"] is True
    items = client.get(f"/business/{OWNER}/purchases/{rd['transaction_id']}/receipt/sample", headers=h).json()
    assert items
    attached = client.post(f"/business/{OWNER}/purchases/{rd['transaction_id']}/receipt", json={"items": [{**i, "create_inventory_item": True} for i in items]}, headers=h)
    assert attached.status_code == 200, attached.text
    assert attached.json()["receipt"]["items"]
    assert client.get(f"/business/{OWNER}/books/trial-balance", headers=h).json()["balanced"] is True


def test_finance_routes_are_tenant_guarded():
    intruder = auth_headers(INTRUDER)
    for path in ("overview", "catalog", "inventory", "orders", "purchases", "books/journal", "analytics/health", "customers"):
        assert client.get(f"/business/{OWNER}/{path}", headers=intruder).status_code == 403, path
        assert client.get(f"/business/{OWNER}/{path}").status_code == 401, path
    assert client.post(f"/business/{OWNER}/assistant/ask", json={"question": "ventas"}, headers=intruder).status_code == 403
    # El intruso, en SU negocio, no ve nada del otro.
    own = client.get(f"/business/{INTRUDER}/orders", headers=intruder)
    assert own.status_code == 200 and own.json() == []
    assert client.get(f"/business/{INTRUDER}/books/journal", headers=intruder).json() == []


def test_demo_session_provisions_seeded_bakery():
    res = client.post("/demo/session")
    assert res.status_code == 200, res.text
    body = res.json()
    demo_id = body["user"]["user_id"]
    h = {"Authorization": f"Bearer {body['access_token']}"}
    overview = client.get(f"/business/{demo_id}/overview", headers=h).json()
    assert overview["has_data"] and overview["health"]["revenue"]["value"] > 0
    assert overview["health"]["integrity"] == {"trial_balance_balanced": True, "balance_sheet_balanced": True}
    # El onboarding ya había creado el catálogo: la semilla lo reutiliza, no lo duplica.
    accounts = client.get(f"/business/{demo_id}/books/accounts", headers=h).json()
    assert len({a["account_number"] for a in accounts}) == len(accounts)
    # Segunda entrada: misma cuenta, sin volver a sembrar.
    again = client.post("/demo/session").json()
    assert again["user"]["user_id"] == demo_id
    ask = client.post(f"/business/{demo_id}/assistant/ask", json={"question": "¿Por qué bajó mi utilidad este mes?"}, headers=h).json()
    assert ask["intent"] == "profit_drivers" and ask["evidence"]
