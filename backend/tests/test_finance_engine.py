"""
Invariantes del motor financiero, directo contra los servicios (sqlite en
memoria, sin HTTP). Cada test corresponde a una regla de negocio que no puede
romperse sin que la demo mienta.
"""


import pytest

from app.db.sqlite_db import SqliteDatabase
from app.finance.accounting import AccountingError, AccountingService, Line
from app.finance.catalog import CatalogError, CatalogService
from app.finance.common import D
from app.finance.demo import DemoSeeder
from app.finance.inventory import InventoryService
from app.finance.payments import DemoPaymentProvider, PaymentEvent
from app.finance.purchases import NormalizedTransaction, PurchaseService
from app.finance.repo import Repo
from app.finance.sales import PaymentMismatch, SalesService


@pytest.fixture
def engine():
    db = SqliteDatabase(":memory:")
    db.ensure_schema()
    repo = Repo(db, "biz_test")
    acc = AccountingService(repo)
    acc.ensure_chart_of_accounts("comida")
    inv = InventoryService(repo, acc)
    cat = CatalogService(repo, inv)
    sales = SalesService(repo, acc, inv, cat)
    purchases = PurchaseService(repo, acc, inv, "comida")
    return {"db": db, "repo": repo, "acc": acc, "inv": inv, "cat": cat, "sales": sales, "purchases": purchases}


def _bakery(e):
    flour = e["inv"].create_item(name="Harina", unit_of_measure="kg", initial_quantity=20, initial_unit_cost="0.80")
    eggs = e["inv"].create_item(name="Huevo", unit_of_measure="pieza", initial_quantity=60, initial_unit_cost="0.20")
    cake = e["cat"].create_item(
        name="Pastel", item_type="PRODUCT", selling_price=25, tax_rate="0.08",
        components=[
            {"inventory_item_id": flour["inventory_item_id"], "quantity_per_unit": "0.5"},
            {"inventory_item_id": eggs["inventory_item_id"], "quantity_per_unit": 4},
        ],
    )
    return flour, eggs, cake


# --- Partida doble -----------------------------------------------------------


def test_chart_of_accounts_follows_numbering_and_has_types(engine):
    accounts = engine["acc"].list_accounts()
    numbers = [a["account_number"] for a in accounts]
    assert numbers == sorted(numbers)
    by_type = {}
    for a in accounts:
        assert a["normal_balance"] in {"DEBIT", "CREDIT"}
        assert a["financial_statement"] in {"BALANCE_SHEET", "INCOME_STATEMENT"}
        by_type.setdefault(a["account_type"], []).append(a["account_number"])
    assert all(1000 <= n < 2000 for n in by_type["ASSET"])
    assert all(2000 <= n < 3000 for n in by_type["LIABILITY"])
    assert all(3000 <= n < 4000 for n in by_type["EQUITY"])
    assert all(4000 <= n < 5000 for n in by_type["REVENUE"])
    assert all(5000 <= n < 6000 for n in by_type["EXPENSE"])
    # La categoría "comida" agrega su cuenta de empaques; ejecutarlo dos veces no duplica.
    assert any(a["account_subtype"] == "PACKAGING" for a in accounts)
    assert len(engine["acc"].ensure_chart_of_accounts("comida")) == len(accounts)


def test_unbalanced_entry_is_rejected(engine):
    acc = engine["acc"]
    bank = acc.account_by_subtype("BANK")["account_id"]
    rev = acc.account_by_subtype("PRODUCT_REVENUE")["account_id"]
    with pytest.raises(AccountingError):
        acc.post_entry(entry_date=None, description="x", source_type="T", source_id="1", lines=[Line(bank, debit=D(50)), Line(rev, credit=D(49))])
    with pytest.raises(AccountingError):
        acc.post_entry(entry_date=None, description="x", source_type="T", source_id="2", lines=[Line(bank, debit=D(50), credit=D(50)), Line(rev, credit=D(50))])
    with pytest.raises(AccountingError):
        acc.post_entry(entry_date=None, description="x", source_type="T", source_id="3", lines=[Line(bank, debit=D(-5)), Line(rev, credit=D(-5))])
    assert engine["acc"].journal() == []


def test_compound_entry_with_three_lines_balances(engine):
    acc = engine["acc"]
    equip = acc.account_by_subtype("FIXED_ASSET")["account_id"]
    bank = acc.account_by_subtype("BANK")["account_id"]
    loan = acc.account_by_subtype("LOAN")["account_id"]
    entry = acc.post_entry(
        entry_date="2026-09-01", description="Horno", source_type="PURCHASE", source_id="oven",
        lines=[Line(equip, debit=D(10000)), Line(bank, credit=D(4000)), Line(loan, credit=D(6000))],
    )
    assert entry["total_debit"] == entry["total_credit"] == D(10000)
    tb = acc.trial_balance()
    assert tb["balanced"] and tb["total_debit"] == D(10000)


def test_same_source_event_does_not_post_twice(engine):
    acc = engine["acc"]
    bank = acc.account_by_subtype("BANK")["account_id"]
    cap = acc.account_by_subtype("OWNER_CAPITAL")["account_id"]
    first = acc.post_entry(entry_date=None, description="a", source_type="OWNER_CONTRIBUTION", source_id="c1", lines=[Line(bank, debit=D(100)), Line(cap, credit=D(100))])
    second = acc.post_entry(entry_date=None, description="a", source_type="OWNER_CONTRIBUTION", source_id="c1", lines=[Line(bank, debit=D(100)), Line(cap, credit=D(100))])
    assert first["entry_id"] == second["entry_id"]
    assert len(acc.journal()) == 1


# --- Inventario ---------------------------------------------------------------


def test_weighted_average_cost(engine):
    inv = engine["inv"]
    eggs = inv.create_item(name="Huevo", unit_of_measure="pieza", initial_quantity=20, initial_unit_cost="0.30")
    inv.receive(eggs["inventory_item_id"], D(30), D("0.40"), source_type="TEST", source_id="p1")
    item = inv.get_item(eggs["inventory_item_id"])
    assert item["quantity_on_hand"] == D(50)
    assert item["average_unit_cost"] == D("0.3600")  # (20*0.30 + 30*0.40) / 50
    mv = inv.consume(eggs["inventory_item_id"], D(4), source_type="SALE", source_id="o1")
    assert mv["total_cost"] == D("-1.4400")
    assert inv.get_item(eggs["inventory_item_id"])["quantity_on_hand"] == D(46)
    # La bitácora reconstruye el saldo.
    total = sum(D(m["quantity_delta"]) for m in inv.movements(eggs["inventory_item_id"]))
    assert total == D(46)


def test_inventory_count_adjustment_posts_adjusting_entry(engine):
    inv, acc = engine["inv"], engine["acc"]
    flour = inv.create_item(name="Harina", unit_of_measure="kg", initial_quantity=10, initial_unit_cost="1.00")
    result = inv.adjust_count(flour["inventory_item_id"], D(7), reason="merma")
    assert result["delta"] == D(-3)
    assert result["journal_entry"]["is_adjusting"] is True
    unadjusted = acc.trial_balance(adjusted=False)
    adjusted = acc.trial_balance(adjusted=True)
    assert unadjusted["balanced"] and adjusted["balanced"]
    # La merma sólo existe en la balanza ajustada; la no ajustada deja el
    # inventario en su valor previo al conteo.
    assert not any(r["account_subtype"] == "COGS_ADJUSTMENT" for r in unadjusted["rows"])
    assert any(r["account_subtype"] == "COGS_ADJUSTMENT" and r["debit_balance"] == D(3) for r in adjusted["rows"])
    assert next(r for r in unadjusted["rows"] if r["account_subtype"] == "INVENTORY")["debit_balance"] == D(10)
    assert next(r for r in adjusted["rows"] if r["account_subtype"] == "INVENTORY")["debit_balance"] == D(7)
    assert acc.income_statement(None, None)["total_cogs"] == D(3)
    assert acc.income_statement(None, None, adjusted=False)["total_cogs"] == D(0)


# --- Venta pagada -------------------------------------------------------------


def test_paid_sale_consumes_bom_and_posts_revenue_tax_and_cogs(engine):
    flour, eggs, cake = _bakery(engine)
    sales, inv, acc = engine["sales"], engine["inv"], engine["acc"]
    order = sales.create_order([{"item_id": cake["item_id"], "quantity": 2}])
    assert order["status"] == "AWAITING_PAYMENT"
    assert order["subtotal"] == D(50) and order["tax_total"] == D(4) and order["total"] == D(54)
    assert len(order["checkout_token"]) >= 40
    # Crear la orden NO toca inventario ni libros (sólo existen los asientos
    # de la existencia inicial, que son aportación del dueño).
    assert inv.get_item(flour["inventory_item_id"])["quantity_on_hand"] == D(20)
    assert {e["source_type"] for e in acc.journal()} == {"OWNER_CONTRIBUTION"}

    event = DemoPaymentProvider().charge(order, {"card_last4": "4242"})
    result = sales.complete_payment(event)
    assert result["status"] == "PAID" and not result["already_processed"]
    assert inv.get_item(flour["inventory_item_id"])["quantity_on_hand"] == D(19)  # 2 × 0.5
    assert inv.get_item(eggs["inventory_item_id"])["quantity_on_hand"] == D(52)  # 2 × 4
    assert result["cogs"] == D("2.4000")  # 1 kg × 0.80 + 8 × 0.20
    sale_entry = next(e for e in acc.journal() if e["source_type"] == "SALE_COMPLETED")
    by_number = {ln["account_number"]: ln for ln in sale_entry["lines"]}
    assert by_number[1020]["debit"] == D(54)
    assert by_number[4010]["credit"] == D(50)
    assert by_number[2100]["credit"] == D(4)  # el impuesto no es ingreso
    cogs_entry = next(e for e in acc.journal() if e["source_type"] == "SALE_COGS")
    assert cogs_entry["total_debit"] == D("2.4")
    assert acc.trial_balance()["balanced"]
    bs = acc.balance_sheet()
    assert bs["balanced"]
    inc = acc.income_statement(None, None)
    assert inc["total_revenue"] == D(50) and inc["gross_profit"] == D("47.6")


def test_duplicate_payment_event_is_idempotent(engine):
    _, _, cake = _bakery(engine)
    sales, acc = engine["sales"], engine["acc"]
    order = sales.create_order([{"item_id": cake["item_id"], "quantity": 1}])
    event = DemoPaymentProvider().charge(order, {})
    sales.complete_payment(event)
    again = sales.complete_payment(event)
    assert again["already_processed"] is True
    other_ref = PaymentEvent(**{**event.__dict__, "provider_ref": "demo_other"})
    third = sales.complete_payment(other_ref)
    assert third["already_processed"] is True
    assert len([e for e in acc.journal() if e["source_type"] == "SALE_COMPLETED"]) == 1
    assert len(engine["repo"].find("payments")) == 1


def test_payment_amount_must_match_order(engine):
    _, _, cake = _bakery(engine)
    order = engine["sales"].create_order([{"item_id": cake["item_id"], "quantity": 1}])
    bad = PaymentEvent(provider="demo", provider_ref="x", order_id=order["order_id"], amount=D(1), currency="USD", status="SUCCEEDED")
    with pytest.raises(PaymentMismatch):
        engine["sales"].complete_payment(bad)
    assert engine["sales"].get_order(order["order_id"])["status"] == "AWAITING_PAYMENT"


def test_failed_payment_has_no_financial_effect(engine):
    flour, _, cake = _bakery(engine)
    order = engine["sales"].create_order([{"item_id": cake["item_id"], "quantity": 1}])
    event = DemoPaymentProvider().charge(order, {"simulate": "fail"})
    result = engine["sales"].complete_payment(event)
    assert result["status"] == "FAILED"
    assert engine["inv"].get_item(flour["inventory_item_id"])["quantity_on_hand"] == D(20)
    assert not any(e["source_type"].startswith("SALE") for e in engine["acc"].journal())
    assert engine["sales"].get_order(order["order_id"])["status"] == "AWAITING_PAYMENT"


# --- Compras con tarjeta -------------------------------------------------------


def test_card_purchase_is_classified_posted_and_reclassified(engine):
    purchases, acc = engine["purchases"], engine["acc"]
    tx = purchases.ingest([NormalizedTransaction("demo", "t1", "2026-09-10T10:00:00", D("100"), "DEBIT", "Restaurant Depot", "RD", "")])[0]
    assert tx["classification_kind"] == "INVENTORY" and tx["classification_status"] == "CLASSIFIED"
    # Reingestar el mismo id del proveedor no duplica.
    assert purchases.ingest([NormalizedTransaction("demo", "t1", "2026-09-10T10:00:00", D("100"), "DEBIT", "Restaurant Depot", "RD", "")]) == []
    amazon = purchases.ingest([NormalizedTransaction("demo", "t2", "2026-09-10T11:00:00", D("129.99"), "DEBIT", "Amazon", "AMZN", "")])[0]
    assert amazon["classification_status"] == "NEEDS_REVIEW"
    # Aun sin confirmar, el pasivo de la tarjeta ya está en libros.
    card = acc.account_by_subtype("CARD")
    assert acc.balances()[card["account_id"]]["balance"] == D("229.99")
    fixed = purchases.classify(amazon["transaction_id"], "EQUIPMENT")
    assert fixed["classification_status"] == "CLASSIFIED" and fixed["account_name"] == "Equipo"
    reclass = [e for e in acc.journal() if e["source_type"] == "RECLASSIFICATION"]
    assert len(reclass) == 1
    assert acc.balances()[acc.account_by_subtype("FIXED_ASSET")["account_id"]]["balance"] == D("129.99")
    assert acc.balances()[acc.account_by_subtype("SUPPLIES")["account_id"]]["balance"] == D(0)
    # El negocio aprendió: la siguiente compra en Amazon ya sale como equipo.
    again = purchases.ingest([NormalizedTransaction("demo", "t3", "2026-09-11T11:00:00", D("20"), "DEBIT", "Amazon", "AMZN", "")])[0]
    assert again["classification_kind"] == "EQUIPMENT" and again["classification_status"] == "CLASSIFIED"
    assert acc.trial_balance()["balanced"]


def test_receipt_enrichment_updates_inventory_quantities(engine):
    purchases, inv = engine["purchases"], engine["inv"]
    inv.create_item(name="Harina", unit_of_measure="kg", initial_quantity=5, initial_unit_cost="0.70")
    tx = purchases.ingest([NormalizedTransaction("demo", "t1", "2026-09-10T10:00:00", D("152.60"), "DEBIT", "Restaurant Depot", "RD", "")])[0]
    items = purchases.sample_receipt(tx["transaction_id"])
    assert items and items[0]["inventory_item_name"] == "Harina"
    assert abs(sum(i["total_cost"] for i in items) - D("152.60")) < D("0.5")
    enriched = purchases.attach_receipt(tx["transaction_id"], [{**i, "create_inventory_item": True} for i in items])
    assert enriched["receipt"]["items"]
    flour = inv.find_by_name("Harina")
    assert D(flour["quantity_on_hand"]) == D(20)  # 5 + 15
    assert engine["acc"].trial_balance()["balanced"]


# --- Aislamiento por negocio ------------------------------------------------------


def test_business_a_cannot_see_business_b(engine):
    _, _, cake = _bakery(engine)
    engine["sales"].create_order([{"item_id": cake["item_id"], "quantity": 1}])
    repo_b = Repo(engine["db"], "biz_other")
    acc_b = AccountingService(repo_b)
    assert acc_b.list_accounts() == []
    inv_b = InventoryService(repo_b, acc_b)
    cat_b = CatalogService(repo_b, inv_b)
    sales_b = SalesService(repo_b, acc_b, inv_b, cat_b)
    assert sales_b.list_orders() == []
    assert cat_b.list_items() == []
    with pytest.raises(CatalogError):
        cat_b.get_item(cake["item_id"])
    with pytest.raises(ValueError):
        repo_b.query("SELECT * FROM sales_orders")  # sin :business_id se rechaza


# --- Demo coherente -------------------------------------------------------------------


def test_demo_seed_is_financially_coherent(engine):
    seeder = DemoSeeder(engine["db"], "biz_test")
    result = seeder.seed()
    assert result["seeded"] and result["orders"] > 100
    acc = engine["acc"]
    acc._invalidate()
    tb = acc.trial_balance()
    assert tb["balanced"]
    bs = acc.balance_sheet()
    assert bs["balanced"] and bs["total_assets"] > 0
    inc = acc.income_statement(None, None)
    assert inc["total_revenue"] > 0 and inc["total_cogs"] > 0 and 0 < inc["total_cogs"] < inc["total_revenue"]
    assert seeder.seed()["seeded"] is False  # no se siembra dos veces
    for item in engine["inv"].list_items():
        assert D(item["quantity_on_hand"]) >= 0, item["name"]
