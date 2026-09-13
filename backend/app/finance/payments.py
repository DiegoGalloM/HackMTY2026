"""
Proveedor de pagos del cobro con QR.

El contrato importante es `PaymentEvent`: el evento AUTORITATIVO de "el
cliente pagó". Un proveedor real lo produciría desde su webhook firmado; el
proveedor demo lo produce al instante. La tubería de venta (sales.py) sólo
conoce el evento, no al proveedor, así que cambiar de demo a real no toca la
contabilidad.

La app nunca guarda números de tarjeta: sólo `card_last4` y la referencia del
proveedor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.finance.common import D, new_id, now_iso


@dataclass
class PaymentEvent:
    provider: str
    provider_ref: str
    order_id: str
    amount: Decimal
    currency: str
    status: str  # SUCCEEDED | FAILED
    method: str = "card"
    card_last4: str | None = None
    customer_name: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    occurred_at: str | None = None


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def charge(self, order: dict[str, Any], payload: dict[str, Any]) -> PaymentEvent:
        """Cobra la orden. Regresa el evento con status SUCCEEDED o FAILED."""

    def describe(self) -> dict[str, Any]:
        return {"provider": self.name, "mode": "test" if self.name == "demo" else "live"}


class DemoPaymentProvider(PaymentProvider):
    """Modo de prueba: aprueba el pago y devuelve un evento con la misma forma
    que produciría un webhook real. Acepta opcionalmente los últimos 4 dígitos
    (para mostrarlos en el recibo) y datos voluntarios del cliente."""

    name = "demo"

    def charge(self, order: dict[str, Any], payload: dict[str, Any]) -> PaymentEvent:
        last4 = str(payload.get("card_last4") or "")[-4:] or None
        if last4 and not last4.isdigit():
            last4 = None
        # Un número completo de tarjeta jamás entra al sistema: si llegara,
        # se descarta y sólo se conservan los últimos 4 dígitos.
        outcome = str(payload.get("simulate") or "success").lower()
        return PaymentEvent(
            provider=self.name,
            provider_ref=f"demo_{new_id()}",
            order_id=order["order_id"],
            amount=D(order["total"]),
            currency=order.get("currency") or "USD",
            status="FAILED" if outcome == "fail" else "SUCCEEDED",
            method=str(payload.get("method") or "card"),
            card_last4=last4,
            customer_name=(payload.get("customer_name") or None),
            customer_email=(payload.get("customer_email") or None),
            customer_phone=(payload.get("customer_phone") or None),
            occurred_at=now_iso(),
        )


@lru_cache
def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    # Único proveedor implementado en el hackathon. Uno real (Stripe, etc.)
    # entra aquí con la misma interfaz y su webhook construye el PaymentEvent.
    if settings.payment_provider != "demo":
        raise RuntimeError(f"PAYMENT_PROVIDER={settings.payment_provider!r} no está implementado; usa 'demo'")
    return DemoPaymentProvider()
