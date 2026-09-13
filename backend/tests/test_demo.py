"""
Negocios de ejemplo: la estética es tan completa como la panadería (libros
que cuadran, diez semanas de ventas, insumo por agotarse, causa real de la
caída de utilidad, catálogo de cuentas de belleza); sembrar dos veces no
duplica; y la panadería sigue produciendo exactamente la misma historia.
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.config import Settings
from app.db.sqlite_db import SqliteDatabase
from app.finance import demo
from app.finance.common import D, q2
from app.finance.deps import FinanceContext
from app.main import app

client = TestClient(app)


def _ctx(db, business_id, business):
    b = demo.DEMO_BUSINESSES[business]
    return FinanceContext(business_id=business_id, business_name=b.business_name, db=db, settings=Settings(use_snowflake=False), profile=b.profile)


def test_salon_seed_is_complete_and_coherent():
    db = SqliteDatabase(":memory:")
    db.ensure_schema()
    seeder = demo.DemoSeeder(db, "biz_salon", "estetica")
    result = seeder.seed()
    assert result["seeded"] and result["business"] == "estetica" and result["weeks"] == 10
    ctx = _ctx(db, "biz_salon", "estetica")
    acc = ctx.accounting
    assert acc.trial_balance()["balanced"]
    bs = acc.balance_sheet()
    assert bs["balanced"] and bs["total_assets"] > 0
    # Diez semanas de ventas: hay órdenes pagadas en cada una de las 10 semanas.
    weeks = {(date.fromisoformat(o["paid_at"][:10]) - date.fromisoformat(ctx.analytics.resolve_period("all")[0])).days // 7 for o in ctx.sales.list_orders(status="PAID", limit=1000)}
    assert result["orders"] >= 150 and len({w for w in weeks}) >= 10
    # Servicios con receta y venta de producto: ambos aparecen en lo vendido.
    summary = ctx.sales.sales_summary(None, None)
    names = {i["name"] for i in summary["by_item"]}
    assert {"Corte de cabello", "Tinte completo", "Manicure gel"} <= names
    assert any("(venta)" in n for n in names)
    # Al menos un insumo por agotarse (el tinte se queda sin reposición).
    inventory = ctx.inventory.summary()
    assert inventory["low_stock_items"], [i["name"] for i in inventory["items"]]
    assert all(D(i["quantity_on_hand"]) >= 0 for i in inventory["items"])
    # "¿Por qué bajó mi utilidad?" tiene causa real.
    drivers = ctx.analytics.profit_drivers("month")
    assert drivers["drivers"] and drivers["delta"] < 0
    # Catálogo de cuentas de belleza y cifras en pesos (renta de ~$8,000).
    subtypes = {a["account_subtype"] for a in acc.list_accounts()}
    assert "BEAUTY_SUPPLIES" in subtypes and "PACKAGING" not in subtypes
    income = acc.income_statement(None, None)
    rent = next(r for r in income["operating_expenses"] if r["account_subtype"] == "RENT")
    assert rent["amount"] >= D("16000")
    assert income["total_revenue"] > D("100000")
    # Idempotente: sembrar de nuevo sin reset no hace nada.
    assert seeder.seed()["seeded"] is False


def test_salon_assistant_answers_with_salon_evidence():
    db = SqliteDatabase(":memory:")
    db.ensure_schema()
    demo.DemoSeeder(db, "biz_salon2", "estetica").seed()
    ctx = _ctx(db, "biz_salon2", "estetica")
    top = ctx.assistant.ask("¿Qué servicio me deja más ganancia?")
    assert top["intent"] == "top_products" and top["evidence"]
    assert any(e["label"] in {"Corte de cabello", "Tinte completo", "Manicure gel", "Peinado", "Tratamiento capilar"} for e in top["evidence"])
    # El insumo sale de la propia pregunta: sin conversación, cada una se
    # responde sola.
    runout = ctx.assistant.ask("¿Cuándo se me acaba el tinte?")
    assert runout["intent"] == "runout"
    assert runout["evidence"][0]["label"] == "Tinte (tubo)" and "Tinte (tubo)" in runout["answer"]
    otro = ctx.assistant.ask("¿Cuándo se me acaba el esmalte?")
    assert otro["intent"] == "runout" and otro["evidence"][0]["label"] == "Esmalte en gel"


def test_bakery_seed_is_unchanged(monkeypatch):
    """Cifras capturadas antes de refactorizar demo.py en un registro. Con la
    fecha fija, la historia de la panadería es reproducible al centavo."""
    monkeypatch.setattr(demo, "today", lambda: date(2026, 9, 13))
    db = SqliteDatabase(":memory:")
    db.ensure_schema()
    result = demo.DemoSeeder(db, "biz_bakery").seed()
    assert (result["orders"], result["receipts"], result["rows"]) == (317, 15, 7203)
    counts = {t: db.scalar(f"SELECT COUNT(*) FROM {t} WHERE business_id = 'biz_bakery'") for t in ("journal_entries", "journal_lines", "inventory_movements", "sales_orders", "order_lines", "card_transactions", "receipt_items", "business_events")}
    assert counts == {"journal_entries": 698, "journal_lines": 1725, "inventory_movements": 2953, "sales_orders": 317, "order_lines": 570, "card_transactions": 39, "receipt_items": 130, "business_events": 356}
    ctx = _ctx(db, "biz_bakery", "panaderia")
    income = ctx.accounting.income_statement(None, None)
    assert (q2(income["total_revenue"]), q2(income["total_cogs"]), q2(income["total_operating_expenses"])) == (Decimal("8676.00"), Decimal("1691.86"), Decimal("4642.54"))
    assert q2(ctx.accounting.balance_sheet()["total_assets"]) == Decimal("10206.03")
    assert q2(ctx.accounting.trial_balance()["total_debit"]) == Decimal("16616.43")


def test_demo_session_selects_the_business():
    salon = client.post("/demo/session", json={"business": "estetica"})
    assert salon.status_code == 200, salon.text
    body = salon.json()
    assert body["user"]["username"] == "demo_estetica" and body["user"]["business_name"] == "Estética Carolina"
    h = {"Authorization": f"Bearer {body['access_token']}"}
    owner = body["user"]["user_id"]
    profile = client.get(f"/business-profile/{owner}", headers=h).json()
    assert profile["category"] == "belleza" and profile["city"] == "Monterrey"
    overview = client.get(f"/business/{owner}/overview", headers=h).json()
    assert overview["has_data"] and overview["category"] == "belleza"
    assert overview["health"]["integrity"] == {"trial_balance_balanced": True, "balance_sheet_balanced": True}
    # Mismo usuario al volver a entrar; sin cuerpo sigue siendo la panadería.
    assert client.post("/demo/session", json={"business": "estetica"}).json()["user"]["user_id"] == owner
    bakery = client.post("/demo/session")
    assert bakery.status_code == 200 and bakery.json()["user"]["username"] == demo.DEMO_USERNAME
    assert client.post("/demo/session", json={}).json()["user"]["username"] == demo.DEMO_USERNAME
    assert client.post("/demo/session", json={"business": "x"}).status_code == 422
    # Las credenciales del salón sirven en el login normal.
    login = client.post("/auth/login", json={"username": "demo_estetica", "password": "BellezaConNumeros2026"})
    assert login.status_code == 200 and login.json()["user"]["user_id"] == owner
    listing = client.get("/demo/businesses").json()
    assert [b["key"] for b in listing] == ["panaderia", "estetica"] and all("password" not in b for b in listing)


def test_seed_endpoint_accepts_business_choice():
    from tests.conftest import auth_headers, seed_user

    seed_user("seed_choice_owner", "seed_choice_user", business_name="Salón de prueba")
    h = auth_headers("seed_choice_owner")
    assert client.post("/business/seed_choice_owner/demo/seed?business=nope", headers=h).status_code == 422
    res = client.post("/business/seed_choice_owner/demo/seed?business=estetica", headers=h)
    assert res.status_code == 200 and res.json()["seeded"] and res.json()["business"] == "estetica"
    inventory = client.get("/business/seed_choice_owner/inventory", headers=h).json()
    assert any(i["name"] == "Tinte (tubo)" for i in inventory["items"])


def test_demo_accounts_exist_without_pressing_explorar_la_demo():
    """Las credenciales de la demo tienen que servir en *Iniciar sesión* desde
    el arranque. Antes la cuenta sólo nacía dentro de POST /demo/session, así
    que con los stores en memoria un login directo respondía 401."""
    import asyncio

    from app.routers.demo import provision
    from app.security import verify_password
    from app.storage.memory_store import MemoryProfileStore, MemoryUserStore

    users, store = MemoryUserStore(), MemoryProfileStore()
    db = SqliteDatabase(":memory:")
    db.ensure_schema()
    bakery = demo.DEMO_BUSINESSES["panaderia"]
    assert asyncio.run(users.get_user_by_username(bakery.username)) is None

    user = asyncio.run(provision(bakery, users, store, db))
    assert user.username == "demo_panaderia"
    assert verify_password(bakery.password, user.password_hash)
    assert asyncio.run(store.get_profile(user.user_id)).category == "comida"
    entries = db.scalar("SELECT COUNT(*) FROM journal_entries WHERE business_id = :b", {"b": user.user_id})
    assert entries > 0

    # Idempotente: ni duplica la cuenta ni vuelve a sembrar.
    again = asyncio.run(provision(bakery, users, store, db))
    assert again.user_id == user.user_id
    assert db.scalar("SELECT COUNT(*) FROM journal_entries WHERE business_id = :b", {"b": user.user_id}) == entries
