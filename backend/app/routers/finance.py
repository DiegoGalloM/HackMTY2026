"""
API financiera del dueño. Todo cuelga de /business/{owner_id} y nace
protegido por `require_owner` (misma guardia estructural que el perfil).

Secciones: catálogo (productos/servicios), inventario, ventas (órdenes + QR),
compras con tarjeta, libros (diario, mayor, balanza, estados financieros),
análisis (salud, razones, caja, insights) y asistente.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.finance.accounting import AccountingError, Line
from app.finance.catalog import CatalogError
from app.finance.common import D
from app.finance.deps import FinanceContext, get_finance_context, run
from app.finance.inventory import InventoryError
from app.finance.sales import PaymentMismatch, SalesError
from app.models.finance import (
    AdjustmentCreate,
    AssistantAsk,
    ClassifyRequest,
    DepreciationCreate,
    InventoryCount,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryReceive,
    OrderCreate,
    ReceiptAttach,
    SellableItemCreate,
    SellableItemUpdate,
    SimulatePurchase,
    jsonable,
)
from app.routers.deps import require_owner

router = APIRouter(
    prefix="/business/{owner_id}",
    tags=["finance"],
    dependencies=[Depends(require_owner)],
)

Ctx = Depends(get_finance_context)

DOMAIN_ERRORS = (AccountingError, InventoryError, CatalogError, SalesError, ValueError)


def _domain(exc: Exception) -> HTTPException:
    if isinstance(exc, PaymentMismatch):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


async def _call(fn, *args, **kwargs):
    try:
        return jsonable(await run(fn, *args, **kwargs))
    except DOMAIN_ERRORS as exc:
        raise _domain(exc) from exc


# ------------------------------------------------------------- resumen --


@router.get("/overview")
async def overview(ctx: FinanceContext = Ctx):
    def build():
        health = ctx.analytics.health("month")
        return {
            "business_name": ctx.business_name,
            "category": ctx.category,
            "health": health,
            "recent_orders": ctx.sales.list_orders(status="PAID", limit=6),
            "recent_purchases": ctx.purchases.list_transactions(limit=6),
            "pending_review": int(
                ctx.repo.scalar(
                    "SELECT COUNT(*) FROM card_transactions WHERE business_id = :business_id AND classification_status = 'NEEDS_REVIEW'"
                )
                or 0
            ),
            "has_data": ctx.accounting.has_postings(),
        }

    return await _call(build)


# ------------------------------------------------------------ catálogo --


@router.get("/catalog")
async def list_catalog(include_inactive: bool = False, ctx: FinanceContext = Ctx):
    return await _call(ctx.catalog.list_items, include_inactive)


@router.post("/catalog", status_code=status.HTTP_201_CREATED)
async def create_catalog_item(payload: SellableItemCreate, ctx: FinanceContext = Ctx):
    data = payload.model_dump()
    data["components"] = [c.model_dump() for c in payload.components]
    return await _call(lambda: ctx.catalog.create_item(**data))


@router.patch("/catalog/{item_id}")
async def update_catalog_item(item_id: str, payload: SellableItemUpdate, ctx: FinanceContext = Ctx):
    data = payload.model_dump(exclude_unset=True)
    components = data.pop("components", None)
    return await _call(lambda: ctx.catalog.update_item(item_id, components=components, **data))


# ----------------------------------------------------------- inventario --


@router.get("/inventory")
async def inventory_summary(ctx: FinanceContext = Ctx):
    return await _call(ctx.inventory.summary)


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
async def create_inventory_item(payload: InventoryItemCreate, ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.inventory.create_item(**payload.model_dump()))


@router.patch("/inventory/{inventory_item_id}")
async def update_inventory_item(inventory_item_id: str, payload: InventoryItemUpdate, ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.inventory.update_item(inventory_item_id, **payload.model_dump(exclude_unset=True)))


@router.post("/inventory/{inventory_item_id}/receive")
async def receive_inventory(inventory_item_id: str, payload: InventoryReceive, ctx: FinanceContext = Ctx):
    def do():
        # Entrada manual (compra en efectivo, regalo, etc.): inventario contra caja.
        movement = ctx.inventory.receive(
            inventory_item_id, D(payload.quantity), D(payload.unit_cost), source_type="MANUAL_RECEIPT",
            source_id=f"manual-{inventory_item_id}-{movement_seed()}", note=payload.note,
        )
        cost = D(payload.quantity) * D(payload.unit_cost)
        if cost > 0:
            inv = ctx.accounting.account_by_subtype("INVENTORY")
            cash = ctx.accounting.account_by_subtype("CASH")
            ctx.accounting.post_entry(
                entry_date=None, description=f"Compra de insumo: {ctx.inventory.get_item(inventory_item_id)['name']}",
                source_type="MANUAL_RECEIPT", source_id=movement["movement_id"],
                lines=[Line(inv["account_id"], debit=cost), Line(cash["account_id"], credit=cost)],
            )
        return ctx.inventory.get_item(inventory_item_id)

    return await _call(do)


def movement_seed() -> str:
    from app.finance.common import new_id

    return new_id()[:8]


@router.post("/inventory/{inventory_item_id}/count")
async def count_inventory(inventory_item_id: str, payload: InventoryCount, ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.inventory.adjust_count(inventory_item_id, D(payload.counted_quantity), reason=payload.reason))


@router.get("/inventory/movements")
async def inventory_movements(inventory_item_id: str | None = None, limit: int = Query(100, le=500), ctx: FinanceContext = Ctx):
    return await _call(ctx.inventory.movements, inventory_item_id, limit)


# --------------------------------------------------------------- ventas --


@router.get("/orders")
async def list_orders(status_filter: str | None = Query(None, alias="status"), limit: int = Query(50, le=500), ctx: FinanceContext = Ctx):
    return await _call(ctx.sales.list_orders, status_filter, limit)


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, ctx: FinanceContext = Ctx):
    lines = [ln.model_dump() for ln in payload.lines]
    return await _call(lambda: ctx.sales.create_order(lines, note=payload.note))


@router.get("/orders/{order_id}")
async def get_order(order_id: str, ctx: FinanceContext = Ctx):
    return await _call(ctx.sales.get_order, order_id)


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, ctx: FinanceContext = Ctx):
    return await _call(ctx.sales.cancel_order, order_id)


@router.get("/sales/summary")
async def sales_summary(period: str = "month", ctx: FinanceContext = Ctx):
    def do():
        start, end, label = ctx.analytics.resolve_period(period)
        return {**ctx.sales.sales_summary(start, end), "label": label, "by_day": ctx.sales.sales_by_day(start, end)}

    return await _call(do)


@router.get("/customers")
async def customers(ctx: FinanceContext = Ctx):
    return await _call(ctx.sales.customers_summary)


# -------------------------------------------------------------- compras --


@router.get("/purchases")
async def list_purchases(status_filter: str | None = Query(None, alias="status"), limit: int = Query(100, le=500), ctx: FinanceContext = Ctx):
    return await _call(ctx.purchases.list_transactions, status_filter, limit)


@router.post("/purchases/sync")
async def sync_purchases(ctx: FinanceContext = Ctx):
    """Trae las transacciones nuevas del proveedor (Nessie o demo) y las
    normaliza, clasifica y contabiliza. Idempotente por id del proveedor."""
    txs = await ctx.transaction_provider.fetch()
    return await _call(ctx.purchases.ingest, txs)


@router.post("/purchases/simulate", status_code=status.HTTP_201_CREATED)
async def simulate_purchase(payload: SimulatePurchase, ctx: FinanceContext = Ctx):
    """Demo: 'la dueña acaba de pagar con su tarjeta'. Produce una transacción
    nueva por la misma tubería que una real."""
    def do():
        index = payload.scenario
        if index is None:
            index = ctx.repo.scalar("SELECT COUNT(*) FROM card_transactions WHERE business_id = :business_id") or 0
        overrides = {k: v for k, v in {"merchant": payload.merchant, "amount": payload.amount}.items() if v is not None}
        tx = ctx.transaction_provider.simulate(int(index), **overrides)
        created = ctx.purchases.ingest([tx])
        return created[0] if created else None

    return await _call(do)


@router.get("/purchases/spending")
async def spending(period: str = "month", ctx: FinanceContext = Ctx):
    def do():
        start, end, label = ctx.analytics.resolve_period(period)
        return {**ctx.purchases.spending(start, end), "label": label}

    return await _call(do)


@router.get("/purchases/{transaction_id}")
async def get_purchase(transaction_id: str, ctx: FinanceContext = Ctx):
    return await _call(ctx.purchases.get_transaction, transaction_id)


@router.get("/purchases/{transaction_id}/suggestion")
async def purchase_suggestion(transaction_id: str, ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.purchases.suggest(ctx.purchases.get_transaction(transaction_id)))


@router.post("/purchases/{transaction_id}/classify")
async def classify_purchase(transaction_id: str, payload: ClassifyRequest, ctx: FinanceContext = Ctx):
    return await _call(ctx.purchases.classify, transaction_id, payload.kind, payload.account_id, payload.remember)


@router.get("/purchases/{transaction_id}/receipt/sample")
async def sample_receipt(transaction_id: str, ctx: FinanceContext = Ctx):
    return await _call(ctx.purchases.sample_receipt, transaction_id)


@router.post("/purchases/{transaction_id}/receipt")
async def attach_receipt(transaction_id: str, payload: ReceiptAttach, ctx: FinanceContext = Ctx):
    items = [i.model_dump() for i in payload.items]
    return await _call(ctx.purchases.attach_receipt, transaction_id, items, payload.source)


# --------------------------------------------------------------- libros --


@router.get("/books/accounts")
async def accounts(ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.list_accounts)


@router.get("/books/journal")
async def journal(start: str | None = None, end: str | None = None, limit: int = Query(100, le=1000), ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.journal, start, end, limit)


@router.get("/books/journal/{entry_id}")
async def journal_entry(entry_id: str, ctx: FinanceContext = Ctx):
    entry = await _call(ctx.accounting.entry_with_lines, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="asiento no encontrado")
    return entry


@router.get("/books/ledger")
async def general_ledger(start: str | None = None, end: str | None = None, ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.general_ledger, start, end)


@router.get("/books/ledger/{account_id}")
async def account_ledger(account_id: str, start: str | None = None, end: str | None = None, ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.ledger, account_id, start, end)


@router.get("/books/trial-balance")
async def trial_balance(as_of: str | None = None, adjusted: bool = True, ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.trial_balance, as_of, adjusted)


@router.get("/books/income-statement")
async def income_statement(period: str = "month", start: str | None = None, end: str | None = None, adjusted: bool = True, ctx: FinanceContext = Ctx):
    def do():
        s, e = start, end
        if not (s and e):
            s, e, _ = ctx.analytics.resolve_period(period)
        return ctx.accounting.income_statement(s, e, adjusted)

    return await _call(do)


@router.get("/books/balance-sheet")
async def balance_sheet(as_of: str | None = None, adjusted: bool = True, ctx: FinanceContext = Ctx):
    return await _call(ctx.accounting.balance_sheet, as_of, adjusted)


@router.post("/books/adjustments", status_code=status.HTTP_201_CREATED)
async def post_adjustment(payload: AdjustmentCreate, ctx: FinanceContext = Ctx):
    lines = [Line(ln.account_id, debit=D(ln.debit), credit=D(ln.credit), memo=ln.memo) for ln in payload.lines]
    return await _call(lambda: ctx.accounting.post_adjustment(description=payload.description, lines=lines, entry_date=payload.entry_date))


@router.post("/books/depreciation", status_code=status.HTTP_201_CREATED)
async def post_depreciation(payload: DepreciationCreate, ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.accounting.post_depreciation(D(payload.amount), payload.entry_date, payload.memo))


@router.get("/books/events")
async def business_events(limit: int = Query(50, le=500), ctx: FinanceContext = Ctx):
    return await _call(lambda: ctx.repo.find("business_events", order_by="created_at DESC", limit=limit))


# ------------------------------------------------------------- análisis --


@router.get("/analytics/health")
async def health(period: str = "month", ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.health, period)


@router.get("/analytics/ratios")
async def ratios(period: str = "30d", ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.ratios, period)


@router.get("/analytics/cash")
async def cash(period: str = "30d", ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.cash_intelligence, period)


@router.get("/analytics/profit-drivers")
async def profit_drivers(period: str = "month", ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.profit_drivers, period)


@router.get("/analytics/timeseries")
async def timeseries(period: str = "30d", ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.timeseries, period)


@router.get("/analytics/insights")
async def insights(ctx: FinanceContext = Ctx):
    return await _call(ctx.analytics.insights)


# ------------------------------------------------------------ asistente --


@router.post("/assistant/ask")
async def ask(payload: AssistantAsk, ctx: FinanceContext = Ctx):
    return await _call(ctx.assistant.ask, payload.question)


@router.get("/assistant/status")
async def assistant_status(ctx: FinanceContext = Ctx):
    llm = ctx.assistant.llm
    return {"llm_provider": llm.name, "llm_available": llm.available, "language": "es"}
