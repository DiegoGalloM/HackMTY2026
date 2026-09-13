"""
Catálogo de cuentas: plantilla base + cuentas extra por tipo de negocio.

Numeración:
  1000-1999 Activos      3000-3999 Capital       5000-5999 Costos / gastos
  2000-2999 Pasivos      4000-4999 Ingresos

El `subtype` es el contrato con el resto del motor: el servicio de ventas
busca la cuenta BANK, el clasificador la INVENTORY, las razones suman por
subtipo. Los nombres son para el dueño; los subtipos para el código.
"""

from __future__ import annotations

from dataclasses import dataclass

ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE = "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE"
DEBIT, CREDIT = "DEBIT", "CREDIT"
BALANCE_SHEET, INCOME_STATEMENT = "BALANCE_SHEET", "INCOME_STATEMENT"

NORMAL_BALANCE = {ASSET: DEBIT, EXPENSE: DEBIT, LIABILITY: CREDIT, EQUITY: CREDIT, REVENUE: CREDIT}
STATEMENT = {
    ASSET: BALANCE_SHEET,
    LIABILITY: BALANCE_SHEET,
    EQUITY: BALANCE_SHEET,
    REVENUE: INCOME_STATEMENT,
    EXPENSE: INCOME_STATEMENT,
}

# Subtipos que participan en razones de liquidez.
CURRENT_ASSET_SUBTYPES = {"CASH", "BANK", "RECEIVABLE", "INVENTORY", "PREPAID"}
QUICK_ASSET_SUBTYPES = {"CASH", "BANK", "RECEIVABLE"}
CASH_SUBTYPES = {"CASH", "BANK"}
CURRENT_LIABILITY_SUBTYPES = {"PAYABLE", "CARD", "TAX_PAYABLE", "SHORT_TERM_LOAN"}
COGS_SUBTYPES = {"COGS", "COGS_ADJUSTMENT"}


@dataclass(frozen=True)
class AccountTemplate:
    number: int
    name: str
    type: str
    subtype: str
    # Cuentas contra (depreciación acumulada, retiros del dueño) llevan saldo
    # contrario al de su tipo.
    contra: bool = False

    @property
    def normal_balance(self) -> str:
        base = NORMAL_BALANCE[self.type]
        if not self.contra:
            return base
        return CREDIT if base == DEBIT else DEBIT

    @property
    def statement(self) -> str:
        return STATEMENT[self.type]


BASE_TEMPLATE: list[AccountTemplate] = [
    AccountTemplate(1010, "Caja", ASSET, "CASH"),
    AccountTemplate(1020, "Cuenta bancaria del negocio", ASSET, "BANK"),
    AccountTemplate(1100, "Cuentas por cobrar", ASSET, "RECEIVABLE"),
    AccountTemplate(1200, "Inventario", ASSET, "INVENTORY"),
    AccountTemplate(1300, "Pagos por adelantado", ASSET, "PREPAID"),
    AccountTemplate(1500, "Equipo", ASSET, "FIXED_ASSET"),
    AccountTemplate(1510, "Depreciación acumulada", ASSET, "ACCUM_DEPRECIATION", contra=True),
    AccountTemplate(2010, "Cuentas por pagar", LIABILITY, "PAYABLE"),
    AccountTemplate(2050, "Tarjeta de crédito del negocio", LIABILITY, "CARD"),
    AccountTemplate(2100, "Impuesto sobre ventas por pagar", LIABILITY, "TAX_PAYABLE"),
    AccountTemplate(2200, "Préstamos por pagar", LIABILITY, "LOAN"),
    AccountTemplate(3010, "Capital del dueño", EQUITY, "OWNER_CAPITAL"),
    AccountTemplate(3020, "Retiros del dueño", EQUITY, "OWNER_DRAW", contra=True),
    AccountTemplate(3100, "Utilidades retenidas", EQUITY, "RETAINED_EARNINGS"),
    AccountTemplate(4010, "Ventas de productos", REVENUE, "PRODUCT_REVENUE"),
    AccountTemplate(4020, "Ingresos por servicios", REVENUE, "SERVICE_REVENUE"),
    AccountTemplate(4900, "Otros ingresos", REVENUE, "OTHER_REVENUE"),
    AccountTemplate(5010, "Costo de ventas", EXPENSE, "COGS"),
    AccountTemplate(5020, "Mermas y ajustes de inventario", EXPENSE, "COGS_ADJUSTMENT"),
    AccountTemplate(5100, "Insumos y suministros", EXPENSE, "SUPPLIES"),
    AccountTemplate(5200, "Renta", EXPENSE, "RENT"),
    AccountTemplate(5300, "Nómina", EXPENSE, "PAYROLL"),
    AccountTemplate(5400, "Luz, agua e internet", EXPENSE, "UTILITIES"),
    AccountTemplate(5500, "Comisiones por cobro", EXPENSE, "PAYMENT_FEES"),
    AccountTemplate(5600, "Publicidad y marketing", EXPENSE, "MARKETING"),
    AccountTemplate(5700, "Transporte y gasolina", EXPENSE, "TRANSPORT"),
    AccountTemplate(5800, "Software y suscripciones", EXPENSE, "SOFTWARE"),
    AccountTemplate(5850, "Depreciación", EXPENSE, "DEPRECIATION"),
    AccountTemplate(5900, "Otros gastos", EXPENSE, "OTHER_EXPENSE"),
    AccountTemplate(5950, "Impuestos", EXPENSE, "TAX"),
    AccountTemplate(5990, "Intereses", EXPENSE, "INTEREST"),
]

# Extras por categoría del onboarding (frontend/src/onboarding/questions.js).
CATEGORY_EXTRAS: dict[str, list[AccountTemplate]] = {
    "comida": [
        AccountTemplate(5120, "Empaques y desechables", EXPENSE, "PACKAGING"),
    ],
    "retail": [
        AccountTemplate(5160, "Envíos y empaque", EXPENSE, "SHIPPING"),
    ],
    "servicios": [
        AccountTemplate(5170, "Subcontratistas", EXPENSE, "SUBCONTRACTORS"),
    ],
    "belleza": [
        AccountTemplate(5130, "Productos de uso por servicio", EXPENSE, "BEAUTY_SUPPLIES"),
    ],
    "construccion": [
        AccountTemplate(1550, "Herramienta", ASSET, "TOOLS"),
        AccountTemplate(5140, "Materiales de obra", EXPENSE, "MATERIALS"),
        AccountTemplate(5150, "Renta de equipo", EXPENSE, "EQUIPMENT_RENTAL"),
    ],
    "transporte": [
        AccountTemplate(1520, "Vehículo", ASSET, "VEHICLE"),
        AccountTemplate(5710, "Gasolina", EXPENSE, "FUEL"),
        AccountTemplate(5720, "Mantenimiento del vehículo", EXPENSE, "VEHICLE_MAINTENANCE"),
    ],
}


def template_for(category: str | None) -> list[AccountTemplate]:
    extras = CATEGORY_EXTRAS.get((category or "").lower(), [])
    return sorted([*BASE_TEMPLATE, *extras], key=lambda a: a.number)


# Cómo se le explica cada tipo de compra al dueño (clasificación en lenguaje
# de negocio, no de contabilidad) y a qué subtipo de cuenta va el cargo.
CLASSIFICATION_KINDS: dict[str, dict[str, str]] = {
    "INVENTORY": {"label": "Inventario / mercancía", "subtype": "INVENTORY"},
    "EQUIPMENT": {"label": "Equipo o herramienta", "subtype": "FIXED_ASSET"},
    "EXPENSE": {"label": "Gasto del negocio", "subtype": "OTHER_EXPENSE"},
    "PERSONAL": {"label": "Compra personal", "subtype": "OWNER_DRAW"},
    "CARD_PAYMENT": {"label": "Pago de la tarjeta", "subtype": "CARD"},
}
