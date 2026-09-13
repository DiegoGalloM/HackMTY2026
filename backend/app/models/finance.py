"""
Contratos de entrada de la API financiera (Pydantic).

Las respuestas son los dicts que producen los servicios, pasados por
`jsonable()` (Decimal -> float). El contrato de salida vive espejado en
frontend/src/api/types.ts.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


def jsonable(value: Any) -> Any:
    """Decimal -> float (4 decimales), recursivo. Todo lo demás pasa igual."""
    if isinstance(value, Decimal):
        return float(round(value, 4))
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


# ----------------------------------------------------------- inventario --


class InventoryItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit_of_measure: str = Field(default="unidad", max_length=24)
    reorder_point: float | None = Field(default=None, ge=0)
    initial_quantity: float | None = Field(default=None, ge=0)
    initial_unit_cost: float | None = Field(default=None, ge=0)


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    unit_of_measure: str | None = Field(default=None, max_length=24)
    reorder_point: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class InventoryReceive(BaseModel):
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    note: str = Field(default="", max_length=200)


class InventoryCount(BaseModel):
    counted_quantity: float = Field(ge=0)
    reason: str = Field(default="Conteo físico", max_length=200)


# -------------------------------------------------------------- catálogo --


class ComponentInput(BaseModel):
    inventory_item_id: str
    quantity_per_unit: float = Field(gt=0)


class SellableItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    item_type: Literal["PRODUCT", "SERVICE"] = "PRODUCT"
    selling_price: float = Field(ge=0)
    description: str = Field(default="", max_length=500)
    tax_rate: float = Field(default=0, ge=0, le=1)
    emoji: str = Field(default="", max_length=8)
    components: list[ComponentInput] = Field(default_factory=list, max_length=40)


class SellableItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    item_type: Literal["PRODUCT", "SERVICE"] | None = None
    selling_price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=500)
    tax_rate: float | None = Field(default=None, ge=0, le=1)
    emoji: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None
    components: list[ComponentInput] | None = Field(default=None, max_length=40)


# ---------------------------------------------------------------- ventas --


class OrderLineInput(BaseModel):
    item_id: str
    quantity: float = Field(gt=0, le=1000)


class OrderCreate(BaseModel):
    lines: list[OrderLineInput] = Field(min_length=1, max_length=50)
    note: str = Field(default="", max_length=300)


class CheckoutPay(BaseModel):
    """Lo que manda la página pública de pago. Nunca un número de tarjeta."""

    card_last4: str | None = Field(default=None, max_length=4)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_email: str | None = Field(default=None, max_length=160)
    customer_phone: str | None = Field(default=None, max_length=40)
    method: Literal["card", "wallet"] = "card"
    simulate: Literal["success", "fail"] = "success"


# --------------------------------------------------------------- compras --


class ClassifyRequest(BaseModel):
    kind: Literal["INVENTORY", "EQUIPMENT", "EXPENSE", "PERSONAL", "CARD_PAYMENT"]
    account_id: str | None = None
    remember: bool = True


class ReceiptItemInput(BaseModel):
    description: str = Field(default="", max_length=200)
    quantity: float = Field(gt=0)
    unit: str = Field(default="", max_length=24)
    unit_cost: float = Field(ge=0)
    inventory_item_id: str | None = None
    create_inventory_item: bool = False
    suggested_name: str | None = Field(default=None, max_length=120)


class ReceiptAttach(BaseModel):
    items: list[ReceiptItemInput] = Field(min_length=1, max_length=100)
    source: Literal["sample", "upload", "ocr", "manual"] = "sample"


class SimulatePurchase(BaseModel):
    scenario: int | None = Field(default=None, ge=0)
    merchant: str | None = Field(default=None, max_length=120)
    amount: float | None = Field(default=None, gt=0)


# ---------------------------------------------------------------- libros --


class AdjustmentLine(BaseModel):
    account_id: str
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    memo: str = Field(default="", max_length=300)


class AdjustmentCreate(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    entry_date: str | None = None
    lines: list[AdjustmentLine] = Field(min_length=2, max_length=40)


class DepreciationCreate(BaseModel):
    amount: float = Field(gt=0)
    entry_date: str | None = None
    memo: str = Field(default="", max_length=200)


# ------------------------------------------------------------- asistente --


class AssistantAsk(BaseModel):
    question: str = Field(min_length=1, max_length=500)
