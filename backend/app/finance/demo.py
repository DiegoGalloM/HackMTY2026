"""
Negocio de ejemplo: "Panadería La Espiga" (comida, Austin TX, 1 persona).

Diez semanas de historia coherente generadas con la MISMA tubería que usa la
app (compras con tarjeta clasificadas, tickets, recetas, ventas por QR con
pago, depreciación). La narrativa: negocio sano que crece hasta que, en las
últimas dos semanas, el proveedor sube precios (el costo promedio de los
insumos sube) y se venden menos pasteles, así que la utilidad del mes baja
aunque el negocio siga vendiendo. Los jueces pueden preguntar "¿por qué bajó
mi utilidad?" y la respuesta tiene una causa real.

Para que sembrar sea rápido también en Snowflake, la historia se construye
primero en un sqlite en memoria (miles de sentencias) y después se copia por
tabla con inserciones masivas (una por tabla).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.db.base import Database
from app.db.sqlite_db import SqliteDatabase
from app.finance import cache
from app.finance.accounting import AccountingService, Line
from app.finance.catalog import CatalogService
from app.finance.common import D, q4, today
from app.finance.inventory import InventoryService
from app.finance.payments import PaymentEvent
from app.finance.purchases import NormalizedTransaction, PurchaseService
from app.finance.repo import KEYS, Repo
from app.finance.sales import SalesService

DEMO_USERNAME = "demo_panaderia"
DEMO_PASSWORD = "PanDeCadaDia2026"
DEMO_BUSINESS_NAME = "Panadería La Espiga"
DEMO_FULL_NAME = "María Espinoza"
DEMO_BIRTHDATE = "1989-06-14"

DEMO_PROFILE = {
    "category": "comida",
    "category_detail": None,
    "operating_days": ["tue", "wed", "thu", "fri", "sat", "sun"],
    "city": "Austin",
    "employees": "1",
    "answers": {
        "vende_producto_fisico": True,
        "guarda_inventario": True,
        "compra_mayoreo": True,
        "se_ha_quedado_sin_stock": True,
        "compro_de_mas": False,
        "vende_en_local_fijo": True,
        "ingredientes_perecederos": True,
        "vende_bebidas": True,
        "prepara_en_sitio": True,
    },
    "week_description_mode": "text",
    "week_description_text": (
        "Los martes voy a Restaurant Depot por harina, huevo y mantequilla para toda la semana. "
        "Entre semana horneo conchas y galletas temprano; los pasteles son sobre pedido. "
        "Los fines de semana vendo más del doble, sobre todo pastel de chocolate y café."
    ),
    "week_description_audio_base64": None,
    "week_description_audio_mime": None,
}

CUSTOMERS = [
    ("Ana Torres", "ana.torres@example.com"),
    ("Luis Cárdenas", "luis.cardenas@example.com"),
    ("Sofía Reyes", "sofia.reyes@example.com"),
    ("Diego Molina", "diego.molina@example.com"),
]


def _ts(day: datetime, hour: int, minute: int = 0) -> str:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


class DemoSeeder:
    def __init__(self, db: Database, business_id: str):
        self.db = db
        self.business_id = business_id

    # ----------------------------------------------------------- API --

    def has_data(self) -> bool:
        return bool(self.db.scalar("SELECT COUNT(*) FROM journal_entries WHERE business_id = :b", {"b": self.business_id}))

    def clear(self) -> None:
        for table in KEYS:
            self.db.execute(f"DELETE FROM {table} WHERE business_id = :b", {"b": self.business_id})
        cache.invalidate_prefix(("accounts", getattr(self.db, "instance_id", None) or id(self.db), self.business_id))

    def seed(self, reset: bool = False, weeks: int = 10) -> dict[str, Any]:
        if self.has_data():
            if not reset:
                return {"seeded": False, "reason": "already_has_data"}
            self.clear()
        # El onboarding pudo haber creado ya el catálogo de cuentas del negocio:
        # la historia se construye SOBRE esas mismas cuentas (mismos ids), no
        # sobre un catálogo paralelo que dejaría cuentas duplicadas.
        existing_accounts = self.db.rows("SELECT * FROM accounts WHERE business_id = :b", {"b": self.business_id})
        # 1) Historia completa en sqlite en memoria, con la tubería real.
        scratch = SqliteDatabase(":memory:")
        scratch.ensure_schema()
        stats = build_history(scratch, self.business_id, weeks=weeks, existing_accounts=existing_accounts)
        # 2) Copia masiva a la base real (una inserción multi-fila por lote).
        known_accounts = {a["account_id"] for a in existing_accounts}
        copied = 0
        with self.db.transaction():
            for table in KEYS:
                rows = scratch.rows(f"SELECT * FROM {table} WHERE business_id = :b", {"b": self.business_id})
                if table == "accounts":
                    rows = [r for r in rows if r["account_id"] not in known_accounts]
                if not rows:
                    continue
                cols = list(rows[0].keys())
                sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
                self.db.execute_many(sql, rows)
                copied += len(rows)
        scratch.close()
        cache.invalidate_prefix(("accounts", getattr(self.db, "instance_id", None) or id(self.db), self.business_id))
        return {"seeded": True, "rows": copied, **stats}


def build_history(db: Database, business_id: str, weeks: int = 10, existing_accounts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rng = random.Random(42)
    repo = Repo(db, business_id)
    acc = AccountingService(repo)
    for row in existing_accounts or []:
        repo.insert("accounts", {k: v for k, v in row.items() if k != "business_id"})
    acc._invalidate()
    acc.ensure_chart_of_accounts("comida")
    inv = InventoryService(repo, acc)
    cat = CatalogService(repo, inv)
    sales = SalesService(repo, acc, inv, cat)
    purchases = PurchaseService(repo, acc, inv, "comida")

    end_day = datetime.combine(today(), datetime.min.time())
    start_day = end_day - timedelta(days=weeks * 7 - 1)
    day0 = start_day

    # Capital inicial del dueño al banco.
    bank = acc.account_by_subtype("BANK")
    capital = acc.account_by_subtype("OWNER_CAPITAL")
    acc.post_entry(
        entry_date=day0.date(), description="Aportación inicial de la dueña", source_type="OWNER_CONTRIBUTION",
        source_id="seed-capital", lines=[Line(bank["account_id"], debit=D("5000")), Line(capital["account_id"], credit=D("5000"))],
    )

    # Insumos con existencia inicial (aportados por la dueña).
    def item(name: str, unit: str, qty: str, cost: str, reorder: str) -> dict[str, Any]:
        return inv.create_item(name=name, unit_of_measure=unit, reorder_point=D(reorder), initial_quantity=D(qty), initial_unit_cost=D(cost), occurred_at=_ts(day0, 8))

    harina = item("Harina de trigo", "kg", "40", "0.72", "15")
    azucar = item("Azúcar", "kg", "20", "0.95", "8")
    huevo = item("Huevo", "pieza", "150", "0.20", "60")
    mantequilla = item("Mantequilla", "kg", "10", "7.60", "4")
    chocolate = item("Chocolate semiamargo", "kg", "8", "10.00", "3")
    leche = item("Leche", "l", "20", "0.92", "8")
    vainilla = item("Vainilla", "l", "1", "18.00", "0.3")
    levadura = item("Levadura", "kg", "2", "9.00", "0.5")
    fresa = item("Fresa", "kg", "4", "6.00", "2")
    crema = item("Crema para batir", "l", "6", "3.00", "2")
    cafe = item("Café en grano", "kg", "4", "14.00", "1")
    vaso = item("Vaso con tapa", "pieza", "300", "0.12", "100")
    caja = item("Caja para pastel", "pieza", "40", "0.85", "15")

    def comp(it: dict[str, Any], qty: str) -> dict[str, Any]:
        return {"inventory_item_id": it["inventory_item_id"], "quantity_per_unit": qty}

    tax = "0.0825"
    pastel_choco = cat.create_item(name="Pastel de chocolate", item_type="PRODUCT", selling_price=D("28"), tax_rate=tax, emoji="🎂", description="Pastel de 8 porciones",
        components=[comp(harina, "0.5"), comp(azucar, "0.35"), comp(huevo, "4"), comp(mantequilla, "0.25"), comp(chocolate, "0.25"), comp(leche, "0.25"), comp(vainilla, "0.01"), comp(caja, "1")])
    pastel_fresa = cat.create_item(name="Pastel de fresas", item_type="PRODUCT", selling_price=D("32"), tax_rate=tax, emoji="🍰", description="Pastel de 8 porciones con fresas",
        components=[comp(harina, "0.45"), comp(azucar, "0.3"), comp(huevo, "4"), comp(mantequilla, "0.2"), comp(fresa, "0.5"), comp(crema, "0.3"), comp(vainilla, "0.01"), comp(caja, "1")])
    concha = cat.create_item(name="Concha", item_type="PRODUCT", selling_price=D("1.75"), tax_rate=tax, emoji="🥐", description="Pan dulce",
        components=[comp(harina, "0.06"), comp(azucar, "0.02"), comp(huevo, "0.2"), comp(mantequilla, "0.012"), comp(levadura, "0.002")])
    galletas = cat.create_item(name="Galletas (docena)", item_type="PRODUCT", selling_price=D("9"), tax_rate=tax, emoji="🍪", description="Docena de galletas con chispas",
        components=[comp(harina, "0.3"), comp(azucar, "0.2"), comp(huevo, "2"), comp(mantequilla, "0.2"), comp(chocolate, "0.1")])
    cafe_item = cat.create_item(name="Café americano", item_type="PRODUCT", selling_price=D("2.75"), tax_rate=tax, emoji="☕", description="12 oz",
        components=[comp(cafe, "0.018"), comp(vaso, "1")])
    clase = cat.create_item(name="Clase de repostería", item_type="SERVICE", selling_price=D("35"), tax_rate="0", emoji="👩‍🍳", description="Clase de 2 horas por persona", components=[])

    # Horno comprado con la tarjeta la primera semana (equipo, no gasto).
    purchases.ingest([NormalizedTransaction("demo", "seed-oven", _ts(day0, 10), D("1800"), "DEBIT", "WebstaurantStore", "WEBSTAURANTSTORE.COM HORNO", "equipment")])

    orders_created = 0
    receipts = 0
    month_paid_card = set()
    fixed_expense_days = set()
    for week in range(weeks):
        week_start = start_day + timedelta(days=week * 7)
        late = week >= weeks - 2  # últimas dos semanas: precios altos y menos pasteles
        price_factor = D("1.18") if late else D("1")

        # Martes: compra grande en Restaurant Depot con ticket (entra inventario).
        tuesday = week_start + timedelta(days=(1 - week_start.weekday()) % 7)
        if tuesday <= end_day:
            amount = q4(D(rng.choice(["132.40", "141.85", "156.20", "138.90"])) * price_factor)
            tx = purchases.ingest([
                NormalizedTransaction("demo", f"seed-rd-{week}", _ts(tuesday, 9, 15), amount, "DEBIT", "Restaurant Depot", "RESTAURANT DEPOT #1123 AUSTIN TX", "wholesale")
            ])[0]
            items = purchases.sample_receipt(tx["transaction_id"])
            purchases.attach_receipt(tx["transaction_id"], [{**i, "create_inventory_item": True} for i in items])
            receipts += 1
        # Jueves: compra chica en H-E-B con ticket cada dos semanas.
        thursday = week_start + timedelta(days=(3 - week_start.weekday()) % 7)
        if week % 2 == 1 and thursday <= end_day:
            amount = q4(D("52.80") * price_factor)
            tx = purchases.ingest([NormalizedTransaction("demo", f"seed-heb-{week}", _ts(thursday, 17, 40), amount, "DEBIT", "H-E-B", "H-E-B #472 AUSTIN TX", "grocery")])[0]
            purchases.attach_receipt(tx["transaction_id"], purchases.sample_receipt(tx["transaction_id"]))
            receipts += 1
        # Gastos con tarjeta de la semana.
        if week % 3 == 0:
            purchases.ingest([NormalizedTransaction("demo", f"seed-uline-{week}", _ts(week_start + timedelta(days=2), 11), D("84.20"), "DEBIT", "Uline", "ULINE SHIP SUPPLIES", "packaging")])
        purchases.ingest([NormalizedTransaction("demo", f"seed-shell-{week}", _ts(week_start + timedelta(days=4), 8, 30), D(rng.choice(["52.10", "58.40", "61.75"])), "DEBIT", "Shell", "SHELL OIL 57444 AUSTIN TX", "fuel")])
        if week % 2 == 0:
            purchases.ingest([NormalizedTransaction("demo", f"seed-meta-{week}", _ts(week_start + timedelta(days=1), 12), D("40.00"), "DEBIT", "Meta Ads", "FACEBK ADS *K3H2", "advertising")])
        if week == 3:
            purchases.ingest([NormalizedTransaction("demo", "seed-amazon", _ts(week_start + timedelta(days=3), 20, 5), D("129.99"), "DEBIT", "Amazon", "AMAZON.COM*2K4LP9 SEATTLE WA", "online")])
        if week == 6:
            purchases.ingest([NormalizedTransaction("demo", "seed-netflix", _ts(week_start + timedelta(days=5), 21), D("15.99"), "DEBIT", "Netflix", "NETFLIX.COM", "subscription")])

        # Gastos fijos mensuales pagados desde el banco (renta, luz, internet, ayudante).
        for day in (week_start + timedelta(days=d) for d in range(7)):
            if day > end_day:
                break
            if day.day == 1 and day.date() not in fixed_expense_days:
                fixed_expense_days.add(day.date())
                _bank_expense(acc, "RENT", D("650"), day, "Renta del local")
                _bank_expense(acc, "UTILITIES", D(rng.choice(["138.40", "142.00", "151.20"])), day, "Austin Energy + internet")
                _bank_expense(acc, "SOFTWARE", D("29.00"), day, "Square POS suscripción")
                acc.post_depreciation(D("30"), entry_date=day.date().isoformat(), memo="Depreciación mensual del horno")
            if day.day == 15 or day.day == 30:
                _bank_expense(acc, "PAYROLL", D("420"), day, "Ayudante de fin de semana")
            if day.day == 20 and day.month not in month_paid_card:
                month_paid_card.add(day.month)
                purchases.ingest([NormalizedTransaction("demo", f"seed-cardpay-{day.month}", _ts(day, 9), D("1500") if week > 0 else D("900"), "CREDIT", "Capital One", "CAPITAL ONE ONLINE PMT", "payment")])

        # Ventas diarias (martes a domingo; fin de semana vende el doble).
        for d in range(7):
            day = week_start + timedelta(days=d)
            if day > end_day or day.weekday() == 0:
                continue
            weekend = day.weekday() >= 4
            base = 7 if weekend else 3
            n_orders = max(1, base + rng.randint(-1, 2))
            if late:
                n_orders = max(1, n_orders - 1)
            for k in range(n_orders):
                hour = rng.randint(8, 18)
                lines = _pick_lines(rng, weekend, late, pastel_choco, pastel_fresa, concha, galletas, cafe_item, clase)
                when = _ts(day, hour, rng.randint(0, 59))
                order = sales.create_order(lines, created_at=when)
                customer = rng.choice(CUSTOMERS) if rng.random() < 0.35 else None
                event = PaymentEvent(
                    provider="demo", provider_ref=f"demo_seed_{week}_{d}_{k}", order_id=order["order_id"], amount=D(order["total"]), currency="USD",
                    status="SUCCEEDED", method="card", card_last4=str(rng.randint(1000, 9999)),
                    customer_name=customer[0] if customer else None, customer_email=customer[1] if customer else None, occurred_at=when,
                )
                sales.complete_payment(event)
                orders_created += 1

    return {"orders": orders_created, "receipts": receipts, "weeks": weeks}


def _bank_expense(acc: AccountingService, subtype: str, amount: Decimal, day: datetime, memo: str) -> None:
    bank = acc.account_by_subtype("BANK")
    exp = acc.account_by_subtype(subtype)
    acc.post_entry(
        entry_date=day.date(), description=memo, source_type="EXPENSE_PAID", source_id=f"seed-{subtype}-{day.date()}",
        lines=[Line(exp["account_id"], debit=amount, memo=memo), Line(bank["account_id"], credit=amount)],
    )


def _pick_lines(rng: random.Random, weekend: bool, late: bool, choco, fresa, concha, galletas, cafe, clase) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    roll = rng.random()
    cake_chance = (0.55 if weekend else 0.25) * (0.6 if late else 1.0)
    if roll < cake_chance:
        lines.append({"item_id": (choco if rng.random() < 0.65 else fresa)["item_id"], "quantity": 1 if rng.random() < 0.85 else 2})
    if rng.random() < 0.7:
        lines.append({"item_id": concha["item_id"], "quantity": rng.randint(2, 8)})
    if rng.random() < 0.45:
        lines.append({"item_id": cafe["item_id"], "quantity": rng.randint(1, 3)})
    if rng.random() < 0.2:
        lines.append({"item_id": galletas["item_id"], "quantity": 1})
    if weekend and rng.random() < 0.08:
        lines.append({"item_id": clase["item_id"], "quantity": rng.randint(1, 3)})
    if not lines:
        lines.append({"item_id": concha["item_id"], "quantity": 3})
    return lines
