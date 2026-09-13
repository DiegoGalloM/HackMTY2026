"""
Página pública de pago: lo que abre el cliente al escanear el QR.

Sin token de sesión: el `checkout_token` de la orden (256 bits aleatorios)
es la credencial. Es la ÚNICA ruta que localiza una orden sin business_id
en la URL; una vez encontrada, todo se hace con el Repo de ESE negocio.

El POST cobra a través del proveedor de pagos y pasa el PaymentEvent
resultante a la tubería de venta: la misma puerta que usaría un webhook.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.db import get_db
from app.db.base import Database
from app.finance.deps import FinanceContext, run
from app.finance.payments import get_payment_provider
from app.finance.sales import PaymentMismatch, SalesError
from app.models.finance import CheckoutPay, jsonable
from app.storage import get_user_store
from app.storage.base import UserStore

router = APIRouter(prefix="/pay", tags=["checkout"])


async def _context_for_token(token: str, db: Database, users: UserStore) -> tuple[FinanceContext, dict]:
    if not token or len(token) < 20:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    row = await run(db.row, "SELECT business_id, order_id FROM sales_orders WHERE checkout_token = :t", {"t": token})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    owner = await users.get_user_by_id(row["business_id"])
    ctx = FinanceContext(
        business_id=row["business_id"],
        business_name=owner.business_name if owner else "Negocio",
        db=db,
        settings=get_settings(),
    )
    order = await run(ctx.sales.get_order, row["order_id"])
    return ctx, order


def _public_view(ctx: FinanceContext, order: dict) -> dict:
    return jsonable(
        {
            "business_name": ctx.business_name,
            "order_number": order["order_number"],
            "status": order["status"],
            "currency": order["currency"],
            "lines": [
                {"item_name": ln["item_name"], "quantity": ln["quantity"], "unit_price": ln["unit_price"], "line_total": ln["line_total"]}
                for ln in order["lines"]
            ],
            "subtotal": order["subtotal"],
            "tax_total": order["tax_total"],
            "total": order["total"],
            "paid_at": order["paid_at"],
            "payment": (
                {"card_last4": order["payment"]["card_last4"], "provider": order["payment"]["provider"], "confirmed_at": order["payment"]["confirmed_at"]}
                if order.get("payment")
                else None
            ),
            "provider": get_payment_provider().describe(),
        }
    )


@router.get("/{token}")
async def get_checkout(token: str, db: Database = Depends(get_db), users: UserStore = Depends(get_user_store)):  # noqa: B008
    ctx, order = await _context_for_token(token, db, users)
    return _public_view(ctx, order)


@router.post("/{token}")
async def pay(token: str, payload: CheckoutPay, db: Database = Depends(get_db), users: UserStore = Depends(get_user_store)):  # noqa: B008
    ctx, order = await _context_for_token(token, db, users)
    if order["status"] == "PAID":
        # Reintento del cliente: se le muestra su recibo, no se cobra dos veces.
        return {**_public_view(ctx, order), "already_paid": True}
    if order["status"] == "CANCELLED":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="order_cancelled")

    provider = get_payment_provider()
    event = provider.charge(order, payload.model_dump())
    try:
        result = await run(ctx.sales.complete_payment, event)
    except PaymentMismatch as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SalesError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result["status"] != "PAID":
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="payment_declined")
    return {**_public_view(ctx, result["order"]), "already_paid": result["already_processed"]}
