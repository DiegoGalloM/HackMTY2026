"""
Negocios de ejemplo (registro `DEMO_BUSINESSES`):

  panaderia  "Panadería La Espiga" (comida, Austin TX, 1 persona). Diez semanas
             de historia coherente: negocio sano que crece hasta que, en las
             últimas dos semanas, el proveedor sube precios y se venden menos
             pasteles, así que la utilidad del mes baja aunque siga vendiendo.
  estetica   "Estética Carolina" (belleza, Monterrey NL, 2 personas). Un
             negocio de SERVICIOS con cifras en pesos: cortes, tintes con
             receta (tubos + oxidante), manicure, venta de producto al público.
             Sábados y quincenas llenas; las últimas dos semanas caen los tintes
             y los insumos suben, así que "¿por qué bajó mi utilidad?" tiene
             una causa real. Misma tubería, otro giro, otro catálogo de cuentas.

Toda la historia se genera con la MISMA tubería que usa la app (compras con
tarjeta clasificadas, tickets, recetas, ventas por QR con pago, conteos,
depreciación), nunca con inserciones a mano. Para que sembrar sea rápido
también en Snowflake, se construye primero en un sqlite en memoria (miles de
sentencias) y después se copia por tabla con inserciones masivas.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
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

# ----------------------------------------------------------- registro --

HistoryBuilder = Callable[[Database, str, int, "list[dict[str, Any]] | None"], dict[str, Any]]


@dataclass(frozen=True)
class DemoBusiness:
    key: str
    username: str
    password: str
    business_name: str
    full_name: str
    birthdate: str
    profile: dict[str, Any]
    build_history: HistoryBuilder
    # Para el selector de la demo y la documentación.
    place: str
    tagline: str

    @property
    def category(self) -> str:
        return self.profile["category"]


# La panadería conserva exactamente sus credenciales, nombres e historia: los
# tests y docs/DEMO.md dependen de ellos.
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

SALON_PROFILE = {
    "category": "belleza",
    "category_detail": None,
    "operating_days": ["tue", "wed", "thu", "fri", "sat"],
    "city": "Monterrey",
    "employees": "2",
    # Respuestas elegidas para que dispare la lección propia de belleza
    # ("¿Cuánto te deja realmente una cita?"): sin quiebres de stock ni
    # sobrecompra en la encuesta, los disparadores genéricos no la tapan.
    "answers": {
        "vende_producto_fisico": True,
        "guarda_inventario": False,
        "compra_mayoreo": False,
        "se_ha_quedado_sin_stock": False,
        "compro_de_mas": False,
        "vende_en_local_fijo": True,
        "usa_insumos_belleza": True,
        "vende_retail": True,
    },
    "week_description_mode": "text",
    "week_description_text": (
        "Los martes paso a Sally Beauty por tintes, oxidante y shampoo para la semana. "
        "Entre semana atiendo cortes y manicure con cita; los sábados se llena de tintes y peinados. "
        "También vendo shampoo y tratamiento a las clientas que lo piden."
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

SALON_CUSTOMERS = [
    ("Fernanda Garza", "fernanda.garza@example.com"),
    ("Valeria Treviño", "valeria.trevino@example.com"),
    ("Mariana Elizondo", "mariana.elizondo@example.com"),
    ("Paola Cantú", "paola.cantu@example.com"),
    ("Regina Villarreal", "regina.villarreal@example.com"),
]


def _ts(day: datetime, hour: int, minute: int = 0) -> str:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


class DemoSeeder:
    def __init__(self, db: Database, business_id: str, business: DemoBusiness | str = "panaderia"):
        self.db = db
        self.business_id = business_id
        self.business = business if isinstance(business, DemoBusiness) else DEMO_BUSINESSES[business]

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
        stats = self.business.build_history(scratch, self.business_id, weeks, existing_accounts)
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
        return {"seeded": True, "rows": copied, "business": self.business.key, **stats}


# ------------------------------------------------------ tubería común --


class Pipeline:
    """Los servicios reales del negocio más las utilidades que comparten las
    historias: insumos con existencia inicial, componentes de receta, compras
    con tarjeta (con o sin ticket), gastos desde el banco y ventas pagadas."""

    def __init__(self, db: Database, business_id: str, category: str, weeks: int, existing_accounts: list[dict[str, Any]] | None, seed: int):
        self.rng = random.Random(seed)
        self.repo = Repo(db, business_id)
        self.acc = AccountingService(self.repo)
        for row in existing_accounts or []:
            self.repo.insert("accounts", {k: v for k, v in row.items() if k != "business_id"})
        self.acc._invalidate()
        self.acc.ensure_chart_of_accounts(category)
        self.inv = InventoryService(self.repo, self.acc)
        self.cat = CatalogService(self.repo, self.inv)
        self.sales = SalesService(self.repo, self.acc, self.inv, self.cat)
        self.purchases = PurchaseService(self.repo, self.acc, self.inv, category)
        self.weeks = weeks
        self.end_day = datetime.combine(today(), datetime.min.time())
        self.start_day = self.end_day - timedelta(days=weeks * 7 - 1)
        self.day0 = self.start_day
        self.orders = 0
        self.receipts = 0
        self._recipes: dict[str, list[dict[str, Any]]] = {}

    # --- capital e insumos ---

    def contribution(self, amount: Decimal, memo: str) -> None:
        bank = self.acc.account_by_subtype("BANK")
        capital = self.acc.account_by_subtype("OWNER_CAPITAL")
        self.acc.post_entry(
            entry_date=self.day0.date(), description=memo, source_type="OWNER_CONTRIBUTION",
            source_id="seed-capital", lines=[Line(bank["account_id"], debit=amount), Line(capital["account_id"], credit=amount)],
        )

    def item(self, name: str, unit: str, qty: str, cost: str, reorder: str) -> dict[str, Any]:
        return self.inv.create_item(name=name, unit_of_measure=unit, reorder_point=D(reorder), initial_quantity=D(qty), initial_unit_cost=D(cost), occurred_at=_ts(self.day0, 8))

    @staticmethod
    def comp(it: dict[str, Any], qty: str) -> dict[str, Any]:
        return {"inventory_item_id": it["inventory_item_id"], "quantity_per_unit": qty}

    # --- calendario ---

    def week_start(self, week: int) -> datetime:
        return self.start_day + timedelta(days=week * 7)

    def weekday(self, week: int, weekday: int) -> datetime:
        """El día `weekday` (0 = lunes) de la semana `week`, o el siguiente."""
        ws = self.week_start(week)
        return ws + timedelta(days=(weekday - ws.weekday()) % 7)

    def days_of(self, week: int) -> list[datetime]:
        ws = self.week_start(week)
        return [d for d in (ws + timedelta(days=i) for i in range(7)) if d <= self.end_day]

    # --- compras con tarjeta ---

    def card(self, ref: str, when: str, amount: Decimal | str, merchant: str, description: str, hint: str, direction: str = "DEBIT") -> dict[str, Any] | None:
        created = self.purchases.ingest([NormalizedTransaction("demo", ref, when, D(amount), direction, merchant, description, hint)])
        return created[0] if created else None

    def card_with_receipt(self, ref: str, when: str, amount: Decimal | str, merchant: str, description: str, hint: str, create_items: bool = True) -> dict[str, Any] | None:
        tx = self.card(ref, when, amount, merchant, description, hint)
        if tx is None:
            return None
        items = self.purchases.sample_receipt(tx["transaction_id"])
        if create_items:
            items = [{**i, "create_inventory_item": True} for i in items]
        self.purchases.attach_receipt(tx["transaction_id"], items)
        self.receipts += 1
        return tx

    def bank_expense(self, subtype: str, amount: Decimal, day: datetime, memo: str) -> None:
        _bank_expense(self.acc, subtype, amount, day, memo)

    def owner_draw(self, amount: Decimal, day: datetime, memo: str) -> None:
        """Retiro del dueño desde el banco: capital (contra), no gasto."""
        bank = self.acc.account_by_subtype("BANK")
        draw = self.acc.account_by_subtype("OWNER_DRAW")
        self.acc.post_entry(
            entry_date=day.date(), description=memo, source_type="OWNER_DRAW", source_id=f"seed-draw-{day.date()}",
            lines=[Line(draw["account_id"], debit=amount, memo=memo), Line(bank["account_id"], credit=amount)],
        )

    # --- ventas ---

    def producible(self, lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Recorta las líneas a lo que la existencia del momento alcanza a
        producir; una línea sin nada que producir se quita.

        Sin esto la historia depende del día en que se siembra: la ventana de
        10 semanas termina hoy, así que cuántos fines de semana (y pasteles)
        caen antes de cada resurtido cambia con la fecha, y algunos días un
        insumo que no se resurte (la caja para pastel) acababa en negativo.
        Nunca consume el rng: cuando alcanza para todo, la historia es idéntica.
        """
        on_hand = {i["inventory_item_id"]: D(i["quantity_on_hand"]) for i in self.inv.list_items(include_inactive=True)}
        missing = [ln["item_id"] for ln in lines if ln["item_id"] not in self._recipes]
        self._recipes.update({iid: [] for iid in missing})
        self._recipes.update(self.cat._components_for(missing))
        kept: list[dict[str, Any]] = []
        for line in lines:
            recipe = self._recipes[line["item_id"]]
            quantity = line["quantity"]
            while quantity > 0 and any(on_hand[c["inventory_item_id"]] < D(c["quantity_per_unit"]) * quantity for c in recipe):
                quantity -= 1
            if quantity <= 0:
                continue
            for c in recipe:
                on_hand[c["inventory_item_id"]] -= D(c["quantity_per_unit"]) * quantity
            kept.append({**line, "quantity": quantity})
        return kept

    def sell(self, lines: list[dict[str, Any]], day: datetime, hour: int, ref: str, customers: list[tuple[str, str]], customer_chance: float, currency: str = "USD") -> dict[str, Any] | None:
        """Orden + pago con el proveedor demo. Consume el rng en este orden:
        minuto, tirada de cliente, cliente, últimos 4 dígitos. Si la existencia
        no alcanza para ninguna línea, no hay venta (y no se consume el rng)."""
        lines = self.producible(lines)
        if not lines:
            return None
        rng = self.rng
        when = _ts(day, hour, rng.randint(0, 59))
        order = self.sales.create_order(lines, created_at=when, currency=currency)
        customer = rng.choice(customers) if rng.random() < customer_chance else None
        event = PaymentEvent(
            provider="demo", provider_ref=ref, order_id=order["order_id"], amount=D(order["total"]), currency=currency,
            status="SUCCEEDED", method="card", card_last4=str(rng.randint(1000, 9999)),
            customer_name=customer[0] if customer else None, customer_email=customer[1] if customer else None, occurred_at=when,
        )
        self.sales.complete_payment(event)
        self.orders += 1
        return order

    def stats(self) -> dict[str, Any]:
        return {"orders": self.orders, "receipts": self.receipts, "weeks": self.weeks}


# ------------------------------------------------------- panadería --


def build_history(db: Database, business_id: str, weeks: int = 10, existing_accounts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Panadería La Espiga. El orden de las operaciones (y del rng) se conserva
    tal cual: la historia es reproducible y los tests dependen de sus cifras."""
    p = Pipeline(db, business_id, "comida", weeks, existing_accounts, seed=42)
    rng, acc, cat, purchases = p.rng, p.acc, p.cat, p.purchases
    end_day, day0 = p.end_day, p.day0

    # Capital inicial del dueño al banco.
    p.contribution(D("5000"), "Aportación inicial de la dueña")

    # Insumos con existencia inicial (aportados por la dueña).
    item, comp = p.item, p.comp
    harina = item("Harina de trigo", "kg", "40", "0.72", "15")
    azucar = item("Azúcar", "kg", "20", "0.95", "8")
    huevo = item("Huevo", "pieza", "150", "0.20", "60")
    mantequilla = item("Mantequilla", "kg", "10", "7.60", "4")
    chocolate = item("Chocolate semiamargo", "kg", "8", "10.00", "3")
    leche = item("Leche", "l", "20", "0.92", "8")
    vainilla = item("Vainilla", "l", "1", "18.00", "0.3")
    levadura = item("Levadura", "kg", "2", "9.00", "0.5")
    fresa = item("Fresa", "kg", "11", "6.3543", "2")
    crema = item("Crema para batir", "l", "7", "3.00", "2")
    cafe = item("Café en grano", "kg", "4", "14.00", "1")
    vaso = item("Vaso con tapa", "pieza", "300", "0.12", "100")
    caja = item("Caja para pastel", "pieza", "50", "0.85", "15")

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
    p.card("seed-oven", _ts(day0, 10), "1800", "WebstaurantStore", "WEBSTAURANTSTORE.COM HORNO", "equipment")

    month_paid_card = set()
    fixed_expense_days = set()
    for week in range(weeks):
        week_start = p.week_start(week)
        late = week >= weeks - 2  # últimas dos semanas: precios altos y menos pasteles
        price_factor = D("1.18") if late else D("1")

        # Martes: compra grande en Restaurant Depot con ticket (entra inventario).
        tuesday = p.weekday(week, 1)
        if tuesday <= end_day:
            amount = q4(D(rng.choice(["132.40", "141.85", "156.20", "138.90"])) * price_factor)
            p.card_with_receipt(f"seed-rd-{week}", _ts(tuesday, 9, 15), amount, "Restaurant Depot", "RESTAURANT DEPOT #1123 AUSTIN TX", "wholesale", create_items=True)
        # Jueves: compra chica en H-E-B con ticket cada dos semanas.
        thursday = p.weekday(week, 3)
        if week % 2 == 1 and thursday <= end_day:
            amount = q4(D("52.80") * price_factor)
            p.card_with_receipt(f"seed-heb-{week}", _ts(thursday, 17, 40), amount, "H-E-B", "H-E-B #472 AUSTIN TX", "grocery", create_items=False)
        # Gastos con tarjeta de la semana.
        if week % 3 == 0:
            p.card(f"seed-uline-{week}", _ts(week_start + timedelta(days=2), 11), "84.20", "Uline", "ULINE SHIP SUPPLIES", "packaging")
        p.card(f"seed-shell-{week}", _ts(week_start + timedelta(days=4), 8, 30), rng.choice(["52.10", "58.40", "61.75"]), "Shell", "SHELL OIL 57444 AUSTIN TX", "fuel")
        if week % 2 == 0:
            p.card(f"seed-meta-{week}", _ts(week_start + timedelta(days=1), 12), "40.00", "Meta Ads", "FACEBK ADS *K3H2", "advertising")
        if week == 3:
            p.card("seed-amazon", _ts(week_start + timedelta(days=3), 20, 5), "129.99", "Amazon", "AMAZON.COM*2K4LP9 SEATTLE WA", "online")
        if week == 6:
            p.card("seed-netflix", _ts(week_start + timedelta(days=5), 21), "15.99", "Netflix", "NETFLIX.COM", "subscription")

        # Gastos fijos mensuales pagados desde el banco (renta, luz, internet, ayudante).
        for day in p.days_of(week):
            if day.day == 1 and day.date() not in fixed_expense_days:
                fixed_expense_days.add(day.date())
                p.bank_expense("RENT", D("650"), day, "Renta del local")
                p.bank_expense("UTILITIES", D(rng.choice(["138.40", "142.00", "151.20"])), day, "Austin Energy + internet")
                p.bank_expense("SOFTWARE", D("29.00"), day, "Square POS suscripción")
                acc.post_depreciation(D("30"), entry_date=day.date().isoformat(), memo="Depreciación mensual del horno")
            if day.day == 15 or day.day == 30:
                p.bank_expense("PAYROLL", D("420"), day, "Ayudante de fin de semana")
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
                p.sell(lines, day, hour, f"demo_seed_{week}_{d}_{k}", CUSTOMERS, 0.35)

    return p.stats()


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


# ---------------------------------------------------------- estética --


def build_salon_history(db: Database, business_id: str, weeks: int = 10, existing_accounts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Estética Carolina: salón de dos personas en Monterrey, cifras en pesos.

    Diez semanas con la misma tubería: insumos que se consumen por servicio
    (tinte = 2 tubos + oxidante), producto al público, compras semanales en
    Sally Beauty con ticket, renta y servicios desde el banco, nómina de la
    estilista asistente, un conteo con merma, un pago de tarjeta. Sábados y
    quincenas (semanas 3 y 6) van llenas; las últimas dos semanas bajan los
    tintes y suben los insumos: la utilidad del mes cae con causa real.
    """
    p = Pipeline(db, business_id, "belleza", weeks, existing_accounts, seed=2026)
    rng, acc, cat = p.rng, p.acc, p.cat
    end_day = p.end_day

    p.contribution(D("25000"), "Aportación inicial de la dueña")

    item, comp = p.item, p.comp
    tinte = item("Tinte (tubo)", "pieza", "40", "95.00", "20")
    oxidante = item("Oxidante", "l", "6", "180.00", "2")
    shampoo = item("Shampoo profesional", "l", "8", "220.00", "3")
    esmalte = item("Esmalte en gel", "pieza", "18", "120.00", "8")
    toallas = item("Toallas desechables", "pieza", "300", "4.50", "120")
    guantes = item("Guantes (par)", "pieza", "200", "3.00", "60")
    ampolleta = item("Ampolleta de tratamiento", "pieza", "24", "85.00", "8")
    kerastase = item("Shampoo Kérastase 250 ml", "pieza", "12", "260.00", "4")
    olaplex = item("Olaplex No. 3", "pieza", "10", "380.00", "3")

    tax = "0.16"  # IVA
    corte = cat.create_item(name="Corte de cabello", item_type="SERVICE", selling_price=D("250"), tax_rate=tax, emoji="✂️", description="Corte y lavado",
        components=[comp(shampoo, "0.02"), comp(toallas, "2")])
    tinte_srv = cat.create_item(name="Tinte completo", item_type="SERVICE", selling_price=D("900"), tax_rate=tax, emoji="🎨", description="Color completo con lavado",
        components=[comp(tinte, "2"), comp(oxidante, "0.09"), comp(shampoo, "0.03"), comp(toallas, "4"), comp(guantes, "1")])
    manicure = cat.create_item(name="Manicure gel", item_type="SERVICE", selling_price=D("350"), tax_rate=tax, emoji="💅", description="Manicure con esmalte en gel",
        components=[comp(esmalte, "0.15"), comp(guantes, "1"), comp(toallas, "1")])
    peinado = cat.create_item(name="Peinado", item_type="SERVICE", selling_price=D("400"), tax_rate=tax, emoji="💇", description="Peinado para evento",
        components=[comp(toallas, "1")])
    tratamiento = cat.create_item(name="Tratamiento capilar", item_type="SERVICE", selling_price=D("550"), tax_rate=tax, emoji="✨", description="Tratamiento reparador",
        components=[comp(ampolleta, "1"), comp(toallas, "2")])
    retail_shampoo = cat.create_item(name="Shampoo Kérastase (venta)", item_type="PRODUCT", selling_price=D("480"), tax_rate=tax, emoji="🧴", description="Botella de 250 ml",
        components=[comp(kerastase, "1")])
    retail_olaplex = cat.create_item(name="Olaplex No. 3 (venta)", item_type="PRODUCT", selling_price=D("650"), tax_rate=tax, emoji="🧴", description="Tratamiento para casa",
        components=[comp(olaplex, "1")])

    # Silla hidráulica comprada con la tarjeta la primera semana (equipo).
    p.card("seed-chair", _ts(p.day0, 11), "4500.00", "Equipos de Belleza MX", "EQUIPOS BELLEZA MX SILLA HIDRAULICA", "equipment")

    busy_weeks = {3, 6}  # quincena y puente: se llena de citas
    shortage_from = weeks - 3  # el proveedor se queda sin el tono de tinte
    month_paid_card = set()
    fixed_expense_days = set()
    counted = False
    for week in range(weeks):
        week_start = p.week_start(week)
        late = week >= weeks - 2  # temporada baja: menos citas, insumos más caros
        price_factor = D("1.15") if late else D("1")

        # Martes: compra de insumos con ticket. Hasta la semana 6 en Sally
        # Beauty (con tubos de tinte); después Sally no tiene el tono y se
        # compra lo demás en Cosmoprof: el tinte se va acabando sin reposición.
        tuesday = p.weekday(week, 1)
        if tuesday <= end_day and week < shortage_from:
            amount = q4(D(rng.choice(["2980.00", "3120.00", "3260.00", "3050.00"])) * price_factor)
            p.card_with_receipt(f"seed-sally-{week}", _ts(tuesday, 10, 20), amount, "Sally Beauty", "SALLY BEAUTY #4410 MONTERREY NL", "beauty_supply", create_items=False)
        elif tuesday <= end_day:
            amount = q4(D(rng.choice(["1980.00", "2060.00"])) * price_factor)
            p.card_with_receipt(f"seed-cosmoprof-{week}", _ts(tuesday, 10, 20), amount, "Cosmoprof", "COSMOPROF MONTERREY NL", "beauty_supply", create_items=False)
        # Jueves: toallas y guantes en Walmart, con ticket.
        thursday = p.weekday(week, 3)
        if thursday <= end_day:
            p.card_with_receipt(f"seed-walmart-{week}", _ts(thursday, 18, 5), q4(D("640.00") * price_factor), "Walmart", "WALMART CUMBRES MONTERREY NL", "grocery", create_items=False)
        # Insumos de uso por servicio sin ticket (van al gasto propio de belleza).
        if week % 3 == 1:
            p.card(f"seed-beautysupply-{week}", _ts(week_start + timedelta(days=2), 12, 30), "680.00", "Beauty Supply MTY", "BEAUTY SUPPLY MTY CENTRO", "beauty_supply")
        p.card(f"seed-uber-{week}", _ts(week_start + timedelta(days=4), 9, 10), rng.choice(["165.00", "180.00", "210.00"]), "Uber", "UBER *TRIP MONTERREY", "transport")
        if week % 2 == 0:
            p.card(f"seed-meta-{week}", _ts(week_start + timedelta(days=1), 13), "500.00", "Meta Ads", "FACEBK ADS *ESTETICA", "advertising")
        if week == 3:
            p.card("seed-amazon", _ts(week_start + timedelta(days=3), 21, 15), "1299.00", "Amazon", "AMAZON MX*SECADORA", "online")
        if week == 5:
            p.card("seed-netflix", _ts(week_start + timedelta(days=5), 22), "219.00", "Netflix", "NETFLIX.COM", "subscription")

        # Gastos fijos desde el banco: renta, luz e internet, agenda, nómina.
        for day in p.days_of(week):
            if day.day == 1 and day.date() not in fixed_expense_days:
                fixed_expense_days.add(day.date())
                p.bank_expense("RENT", D("8000"), day, "Renta del local")
                p.bank_expense("UTILITIES", D(rng.choice(["1380.00", "1420.00", "1510.00"])), day, "CFE + internet")
                p.bank_expense("SOFTWARE", D("349.00"), day, "Agenda de citas (suscripción)")
                acc.post_depreciation(D("75"), entry_date=day.date().isoformat(), memo="Depreciación mensual de la silla")
            if day.day == 15 or day.day == 30:
                p.bank_expense("PAYROLL", D("3500"), day, "Estilista asistente (quincena)")
            if day.day == 5:
                p.owner_draw(D("12000"), day, "Retiro de la dueña")
            if day.day == 20 and day.month not in month_paid_card:
                month_paid_card.add(day.month)
                p.card(f"seed-cardpay-{day.month}", _ts(day, 9), "9000.00" if week > 0 else "6000.00", "Capital One", "CAPITAL ONE ONLINE PMT", "payment", direction="CREDIT")

        # Conteo físico a mitad de la historia: faltan toallas (merma).
        if week == 5 and not counted:
            counted = True
            current = p.inv.get_item(toallas["inventory_item_id"])
            p.inv.adjust_count(toallas["inventory_item_id"], D(current["quantity_on_hand"]) - D("30"), reason="Conteo físico: toallas dañadas", entry_date=p.weekday(week, 0).date().isoformat())

        # Citas de martes a sábado; el sábado se llena.
        for d in range(7):
            day = week_start + timedelta(days=d)
            if day > end_day or day.weekday() in (0, 6):
                continue
            saturday = day.weekday() == 5
            base = 9 if saturday else 6 if day.weekday() == 4 else 4
            n_orders = max(1, base + rng.randint(-1, 2))
            if week in busy_weeks:
                n_orders += 2
            if late:
                n_orders = max(1, n_orders - 2)
            for k in range(n_orders):
                hour = rng.randint(10, 19)
                # Sin tubos suficientes no se agenda un tinte: la venta se
                # pierde (por eso el quiebre de stock duele en la utilidad).
                tint_ok = D(p.inv.get_item(tinte["inventory_item_id"])["quantity_on_hand"]) >= 6
                lines = _pick_salon_lines(rng, saturday, late, tint_ok, corte, tinte_srv, manicure, peinado, tratamiento, retail_shampoo, retail_olaplex)
                p.sell(lines, day, hour, f"demo_salon_{week}_{d}_{k}", SALON_CUSTOMERS, 0.5, currency="MXN")

    return p.stats()


def _pick_salon_lines(rng: random.Random, saturday: bool, late: bool, tint_ok: bool, corte, tinte, manicure, peinado, tratamiento, retail_shampoo, retail_olaplex) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if rng.random() < 0.6:
        lines.append({"item_id": corte["item_id"], "quantity": 1})
    tint_chance = (0.45 if saturday else 0.28) * (0.7 if late else 1.0)
    if rng.random() < tint_chance and tint_ok:
        lines.append({"item_id": tinte["item_id"], "quantity": 1})
    if rng.random() < 0.35:
        lines.append({"item_id": manicure["item_id"], "quantity": 1})
    if rng.random() < (0.35 if saturday else 0.12):
        lines.append({"item_id": peinado["item_id"], "quantity": 1})
    if rng.random() < 0.12:
        lines.append({"item_id": tratamiento["item_id"], "quantity": 1})
    if rng.random() < (0.12 if saturday else 0.07):
        lines.append({"item_id": (retail_shampoo if rng.random() < 0.6 else retail_olaplex)["item_id"], "quantity": 1})
    if not lines:
        lines.append({"item_id": corte["item_id"], "quantity": 1})
    return lines


# ------------------------------------------------------------ registro --

DEMO_BUSINESSES: dict[str, DemoBusiness] = {
    "panaderia": DemoBusiness(
        key="panaderia",
        username=DEMO_USERNAME,
        password=DEMO_PASSWORD,
        business_name=DEMO_BUSINESS_NAME,
        full_name=DEMO_FULL_NAME,
        birthdate=DEMO_BIRTHDATE,
        profile=DEMO_PROFILE,
        build_history=build_history,
        place="Austin, TX",
        tagline="Productos con receta, inventario perecedero y compras al mayoreo con ticket.",
    ),
    "estetica": DemoBusiness(
        key="estetica",
        username="demo_estetica",
        password="BellezaConNumeros2026",
        business_name="Estética Carolina",
        full_name="Carolina Ramírez",
        birthdate="1992-03-21",
        profile=SALON_PROFILE,
        build_history=build_salon_history,
        place="Monterrey, MX",
        tagline="Servicios que consumen insumos, venta de producto y cifras en pesos.",
    ),
}

DEFAULT_DEMO_BUSINESS = "panaderia"
DEMO_BUSINESS_KEYS = tuple(DEMO_BUSINESSES)
