"""
Compras con la tarjeta de negocio.

    proveedor de transacciones (demo | Nessie)
        -> transacción normalizada (lo que el sistema OBSERVÓ)
        -> card_transactions
        -> clasificación (reglas del negocio > reglas por comercio > revisión)
        -> asiento: cargo a la cuenta elegida, abono a la tarjeta
        -> opcional: ticket con artículos -> entradas de inventario

El asiento se publica de inmediato con la mejor clasificación (el lado de la
tarjeta es cierto aunque el otro no), y si el dueño corrige, se publica una
reclasificación: nunca se edita ni se borra un asiento publicado.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.finance import coa
from app.finance.accounting import AccountingError, AccountingService, Line
from app.finance.common import ZERO, D, iso_date, new_id, now_iso, q2, q4
from app.finance.inventory import InventoryService
from app.finance.repo import Repo

AUTO_POST_CONFIDENCE = Decimal("0.80")


@dataclass
class NormalizedTransaction:
    provider: str
    provider_transaction_id: str
    occurred_at: str
    amount: Decimal
    direction: str  # DEBIT = compra | CREDIT = abono/pago a la tarjeta
    merchant: str
    description: str = ""
    category_hint: str = ""


# ------------------------------------------------------------ proveedores --


class TransactionProvider(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> list[NormalizedTransaction]:
        """Transacciones recientes de la tarjeta de negocio."""

    @abstractmethod
    def simulate(self, index: int | None = None, **overrides: Any) -> NormalizedTransaction:
        """Genera una compra nueva "en vivo" para la demo."""


# Escenarios realistas para una micro-empresa de comida en EE. UU. El índice
# rota, así cada clic en "simular compra" cuenta una historia distinta.
DEMO_SCENARIOS: list[dict[str, Any]] = [
    {"merchant": "Restaurant Depot", "amount": "152.60", "description": "RESTAURANT DEPOT #1123 AUSTIN TX", "hint": "wholesale"},
    {"merchant": "Amazon", "amount": "129.99", "description": "AMAZON.COM*2K4LP9 SEATTLE WA", "hint": "online"},
    {"merchant": "Shell", "amount": "58.40", "description": "SHELL OIL 57444 AUSTIN TX", "hint": "fuel"},
    {"merchant": "Austin Energy", "amount": "142.00", "description": "AUSTIN ENERGY UTILITY PMT", "hint": "utilities"},
    {"merchant": "H-E-B", "amount": "52.80", "description": "H-E-B #472 AUSTIN TX", "hint": "grocery"},
    {"merchant": "Uline", "amount": "84.20", "description": "ULINE SHIP SUPPLIES", "hint": "packaging"},
    {"merchant": "WebstaurantStore", "amount": "349.00", "description": "WEBSTAURANTSTORE.COM", "hint": "equipment"},
    {"merchant": "Meta Ads", "amount": "40.00", "description": "FACEBK ADS *K3H2", "hint": "advertising"},
    {"merchant": "Netflix", "amount": "15.99", "description": "NETFLIX.COM", "hint": "subscription"},
    {"merchant": "Capital One", "amount": "600.00", "description": "CAPITAL ONE ONLINE PMT", "hint": "payment", "direction": "CREDIT"},
]

# Tickets de muestra: lo que un OCR/visión extraería. Cantidades en unidades
# compatibles con el inventario de la panadería demo.
SAMPLE_RECEIPTS: dict[str, list[dict[str, Any]]] = {
    "restaurant depot": [
        {"description": "Harina de trigo 5 kg × 3", "quantity": "15", "unit": "kg", "unit_cost": "0.74", "match": "harina"},
        {"description": "Azúcar 4 kg × 2", "quantity": "8", "unit": "kg", "unit_cost": "0.98", "match": "azúcar"},
        {"description": "Huevo (cartón 30) × 3", "quantity": "90", "unit": "pieza", "unit_cost": "0.21", "match": "huevo"},
        {"description": "Mantequilla 1 kg × 6", "quantity": "6", "unit": "kg", "unit_cost": "7.90", "match": "mantequilla"},
        {"description": "Chocolate semiamargo 2.5 kg", "quantity": "2.5", "unit": "kg", "unit_cost": "10.40", "match": "chocolate"},
        {"description": "Leche entera galón", "quantity": "4", "unit": "l", "unit_cost": "0.95", "match": "leche"},
        {"description": "Vainilla 250 ml", "quantity": "0.25", "unit": "l", "unit_cost": "18.50", "match": "vainilla"},
        {"description": "Levadura 500 g", "quantity": "0.5", "unit": "kg", "unit_cost": "9.10", "match": "levadura"},
        {"description": "Café en grano 600 g", "quantity": "0.6", "unit": "kg", "unit_cost": "14.00", "match": "café"},
        {"description": "Vasos 12 oz con tapa × 30", "quantity": "30", "unit": "pieza", "unit_cost": "0.12", "match": "vaso"},
        {"description": "Cajas para pastel × 12", "quantity": "12", "unit": "pieza", "unit_cost": "0.85", "match": "caja"},
    ],
    "h-e-b": [
        {"description": "Fresas 1 lb × 11", "quantity": "5", "unit": "kg", "unit_cost": "6.20", "match": "fresa"},
        {"description": "Leche entera", "quantity": "4", "unit": "l", "unit_cost": "1.05", "match": "leche"},
        {"description": "Huevo docena × 2.5", "quantity": "30", "unit": "pieza", "unit_cost": "0.24", "match": "huevo"},
        {"description": "Crema para batir", "quantity": "3", "unit": "l", "unit_cost": "3.10", "match": "crema"},
    ],
    # Estética (pesos): lo que trae la compra semanal de insumos del salón.
    "sally beauty": [
        {"description": "Tinte permanente tubo × 12", "quantity": "12", "unit": "pieza", "unit_cost": "95.00", "match": "tinte"},
        {"description": "Oxidante 20 vol 1 l × 2", "quantity": "2", "unit": "l", "unit_cost": "180.00", "match": "oxidante"},
        {"description": "Shampoo profesional 1 l × 2", "quantity": "2", "unit": "l", "unit_cost": "220.00", "match": "shampoo profesional"},
        {"description": "Esmalte en gel × 4", "quantity": "4", "unit": "pieza", "unit_cost": "120.00", "match": "esmalte"},
        {"description": "Ampolleta reparadora × 6", "quantity": "6", "unit": "pieza", "unit_cost": "85.00", "match": "ampolleta"},
        {"description": "Shampoo Kérastase 250 ml × 2", "quantity": "2", "unit": "pieza", "unit_cost": "260.00", "match": "kérastase"},
        {"description": "Olaplex No. 3 × 1", "quantity": "1", "unit": "pieza", "unit_cost": "380.00", "match": "olaplex"},
    ],
    # Cuando Sally no tiene el tono: lo mismo sin tinte.
    "cosmoprof": [
        {"description": "Oxidante 20 vol 1 l × 2", "quantity": "2", "unit": "l", "unit_cost": "180.00", "match": "oxidante"},
        {"description": "Shampoo profesional 1 l × 2", "quantity": "2", "unit": "l", "unit_cost": "220.00", "match": "shampoo profesional"},
        {"description": "Esmalte en gel × 4", "quantity": "4", "unit": "pieza", "unit_cost": "120.00", "match": "esmalte"},
        {"description": "Ampolleta reparadora × 6", "quantity": "6", "unit": "pieza", "unit_cost": "85.00", "match": "ampolleta"},
        {"description": "Shampoo Kérastase 250 ml × 2", "quantity": "2", "unit": "pieza", "unit_cost": "260.00", "match": "kérastase"},
        {"description": "Olaplex No. 3 × 1", "quantity": "1", "unit": "pieza", "unit_cost": "380.00", "match": "olaplex"},
    ],
    "walmart": [
        {"description": "Toallas desechables paq. 100", "quantity": "100", "unit": "pieza", "unit_cost": "4.50", "match": "toalla"},
        {"description": "Guantes de nitrilo × 50 pares", "quantity": "50", "unit": "pieza", "unit_cost": "3.00", "match": "guante"},
    ],
}


class DemoTransactionProvider(TransactionProvider):
    name = "demo"

    def __init__(self, seed_offset: int = 0):
        self._cursor = seed_offset

    async def fetch(self) -> list[NormalizedTransaction]:
        return []

    def simulate(self, index: int | None = None, **overrides: Any) -> NormalizedTransaction:
        if index is None:
            index = self._cursor
            self._cursor += 1
        scenario = DEMO_SCENARIOS[index % len(DEMO_SCENARIOS)]
        return NormalizedTransaction(
            provider=self.name,
            provider_transaction_id=f"demo_tx_{new_id()[:12]}",
            occurred_at=overrides.get("occurred_at") or now_iso(),
            amount=D(overrides.get("amount") or scenario["amount"]),
            direction=overrides.get("direction") or scenario.get("direction", "DEBIT"),
            merchant=overrides.get("merchant") or scenario["merchant"],
            description=overrides.get("description") or scenario["description"],
            category_hint=scenario.get("hint", ""),
        )


class NessieTransactionProvider(TransactionProvider):
    """Nessie como UNA fuente más. Sus estructuras no salen de aquí: todo se
    normaliza antes de tocar el motor financiero."""

    name = "nessie"

    def __init__(self, client, account_id: str = "acc_1"):
        self._client = client
        self._account_id = account_id

    async def fetch(self) -> list[NormalizedTransaction]:
        raw = await self._client.list_transactions(self._account_id)
        out = []
        for tx in raw:
            tx_type = tx.get("type", "purchase")
            direction = "CREDIT" if tx_type in {"deposit", "transfer_in"} else "DEBIT"
            desc = tx.get("description") or ""
            merchant = desc.split(" - ")[-1] if " - " in desc else (tx.get("merchant_id") or desc or "Comercio")
            out.append(
                NormalizedTransaction(
                    provider=self.name,
                    provider_transaction_id=str(tx.get("id")),
                    occurred_at=str(tx.get("date") or now_iso())[:19],
                    amount=D(tx.get("amount", 0)),
                    direction=direction,
                    merchant=str(merchant)[:120],
                    description=desc[:300],
                    category_hint=tx_type,
                )
            )
        return out

    def simulate(self, index: int | None = None, **overrides: Any) -> NormalizedTransaction:
        return DemoTransactionProvider().simulate(index, **overrides)


# ---------------------------------------------------------- clasificación --

# (patrón sobre comercio+descripción, tipo, subtipo de cuenta, confianza)
MERCHANT_RULES: list[tuple[str, str, str, str]] = [
    (r"restaurant depot|sysco|us foods|costco|sam'?s club|smart ?& ?final|cash ?& ?carry|wholesale|mayoreo|abasto", "INVENTORY", "INVENTORY", "0.90"),
    (r"h-?e-?b|walmart|kroger|whole foods|trader joe|aldi|fiesta mart|mercado|supermercado|grocery", "INVENTORY", "INVENTORY", "0.82"),
    (r"sally beauty|cosmoprof|beauty supply", "INVENTORY", "INVENTORY", "0.85"),
    (r"home depot|lowe'?s|ferreter|truper|materiales", "INVENTORY", "INVENTORY", "0.70"),
    (r"webstaurant|kitchenaid|best buy|apple store|equipment|equipo|hobart|vulcan", "EQUIPMENT", "FIXED_ASSET", "0.82"),
    (r"uline|packaging|empaque|office depot|staples|dollar tree|papeler", "EXPENSE", "SUPPLIES", "0.85"),
    (r"rent|renta|lease|property mgmt|inmobiliaria", "EXPENSE", "RENT", "0.90"),
    (r"energy|electric|cfe|water|agua|gas co|comcast|spectrum|at&t|verizon|t-mobile|internet|utility", "EXPENSE", "UTILITIES", "0.90"),
    (r"shell|exxon|chevron|valero|pemex|gas station|fuel|uber|lyft|parking", "EXPENSE", "TRANSPORT", "0.88"),
    (r"facebk|meta ads|google ads|instagram|vistaprint|marketing|publicidad", "EXPENSE", "MARKETING", "0.90"),
    (r"square|shopify|quickbooks|canva|adobe|microsoft|google workspace|zoom|dropbox", "EXPENSE", "SOFTWARE", "0.85"),
    (r"gusto|adp|payroll|n[oó]mina|paychex", "EXPENSE", "PAYROLL", "0.92"),
    (r"stripe fee|square fee|comisi[oó]n", "EXPENSE", "PAYMENT_FEES", "0.90"),
    (r"netflix|spotify|hulu|disney|cinema|gym|xbox|playstation", "PERSONAL", "OWNER_DRAW", "0.75"),
    (r"amazon|amzn|ebay|mercado libre|temu", "EXPENSE", "SUPPLIES", "0.45"),
    (r"starbucks|mcdonald|taco|restaurant|cafe|caf[eé]", "EXPENSE", "OTHER_EXPENSE", "0.40"),
]


class PurchaseService:
    def __init__(self, repo: Repo, accounting: AccountingService, inventory: InventoryService, category: str | None = None):
        self.repo = repo
        self.accounting = accounting
        self.inventory = inventory
        self.category = (category or "").lower()

    # ------------------------------------------------------------ ingesta --

    def ingest(self, transactions: list[NormalizedTransaction], auto_post: bool = True) -> list[dict[str, Any]]:
        created = []
        for tx in transactions:
            if self.repo.find_one(
                "card_transactions",
                "provider = :p AND provider_transaction_id = :pid",
                {"p": tx.provider, "pid": tx.provider_transaction_id},
            ):
                continue  # ya la vimos: no se duplica ni se vuelve a contabilizar
            row = {
                "transaction_id": new_id(),
                "provider": tx.provider,
                "provider_transaction_id": tx.provider_transaction_id,
                "occurred_at": tx.occurred_at,
                "amount": q4(abs(tx.amount)),
                "direction": tx.direction,
                "merchant": tx.merchant[:120],
                "description": tx.description[:300],
                "category_hint": tx.category_hint[:60],
                "classification_status": "PENDING",
                "classification_kind": None,
                "classified_account_id": None,
                "confidence": None,
                "classification_reason": None,
                "journal_entry_id": None,
                "receipt_id": None,
                "created_at": now_iso(),
            }
            with self.repo.transaction():
                self.repo.insert("card_transactions", row)
                if auto_post:
                    row = self._auto_classify_and_post(row)
            created.append(self.get_transaction(row["transaction_id"]))
        return created

    def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        tx = self.repo.get("card_transactions", transaction_id)
        if not tx:
            raise ValueError("esa transacción no existe")
        return self._hydrate(tx)

    def _hydrate(self, tx: dict[str, Any]) -> dict[str, Any]:
        return self._hydrate_many([tx])[0]

    def _hydrate_many(self, txs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Tickets de varias transacciones en 2 consultas, no 2 por transacción."""
        receipt_ids = [t["receipt_id"] for t in txs if t.get("receipt_id")]
        receipts: dict[str, dict[str, Any]] = {}
        if receipt_ids:
            params = {f"r{j}": rid for j, rid in enumerate(receipt_ids)}
            placeholders = ", ".join(f":r{j}" for j in range(len(receipt_ids)))
            for r in self.repo.query(f"SELECT * FROM receipts WHERE business_id = :business_id AND receipt_id IN ({placeholders})", params):
                r["items"] = []
                receipts[r["receipt_id"]] = r
            for it in self.repo.query(f"SELECT * FROM receipt_items WHERE business_id = :business_id AND receipt_id IN ({placeholders})", params):
                if it["receipt_id"] in receipts:
                    receipts[it["receipt_id"]]["items"].append(it)
        for tx in txs:
            acc = None
            if tx.get("classified_account_id"):
                try:
                    acc = self.accounting.account(tx["classified_account_id"])
                except AccountingError:
                    acc = None
            tx["account_name"] = acc["account_name"] if acc else None
            tx["kind_label"] = coa.CLASSIFICATION_KINDS.get(tx.get("classification_kind") or "", {}).get("label")
            tx["receipt"] = receipts.get(tx["receipt_id"]) if tx.get("receipt_id") else None
            tx["sample_receipt_available"] = (
                tx["receipt_id"] is None
                and tx["direction"] == "DEBIT"
                and self._sample_receipt(tx["merchant"]) is not None
            )
            tx["needs_review"] = tx["classification_status"] == "NEEDS_REVIEW"
        return txs

    def list_transactions(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where, params = "", {}
        if status:
            where, params = "classification_status = :s", {"s": status}
        rows = self.repo.find("card_transactions", where, params, order_by="occurred_at DESC", limit=limit)
        return self._hydrate_many(rows)

    # ------------------------------------------------------ clasificación --

    def suggest(self, tx: dict[str, Any]) -> dict[str, Any]:
        """Regresa {kind, account_id, confidence, reason, requires_user_confirmation}.
        Determinista. Un LLM podría proponer aquí, pero SIEMPRE se valida
        contra el catálogo: nunca inventa cuentas."""
        if tx["direction"] == "CREDIT":
            card = self.accounting.account_by_subtype("CARD")
            return self._suggestion("CARD_PAYMENT", card, "0.95", "Abono a la tarjeta")

        haystack = f"{tx['merchant']} {tx['description']}".lower()

        # 1) Lo que el negocio ya enseñó.
        for rule in self.repo.find("merchant_rules", order_by="created_at DESC"):
            if rule["merchant_pattern"].lower() in haystack:
                acc = self.accounting.account(rule["account_id"])
                return self._suggestion(rule["classification_kind"], acc, "0.97", f"Así clasificaste {rule['merchant_pattern']} antes")

        # 2) Reglas por comercio, con sesgo por giro del negocio.
        for pattern, kind, subtype, conf in MERCHANT_RULES:
            if re.search(pattern, haystack):
                kind, subtype, conf = self._bias_by_category(kind, subtype, conf, haystack)
                acc = self._account_for(kind, subtype)
                return self._suggestion(kind, acc, conf, f"El comercio parece de {coa.CLASSIFICATION_KINDS[kind]['label'].lower()}")

        # 3) Sin pista: gasto general pero pidiendo confirmación.
        acc = self.accounting.account_by_subtype("OTHER_EXPENSE")
        return self._suggestion("EXPENSE", acc, "0.35", "No reconocimos el comercio")

    def _bias_by_category(self, kind: str, subtype: str, conf: str, haystack: str) -> tuple[str, str, str]:
        # Ejemplos: para construcción, Home Depot es material de obra (gasto por
        # proyecto), no inventario; para transporte, la gasolina va a su cuenta.
        if self.category == "construccion" and re.search(r"home depot|lowe|ferreter|materiales", haystack):
            return "EXPENSE", "MATERIALS", "0.85"
        if self.category == "transporte" and subtype == "TRANSPORT" and re.search(r"shell|exxon|chevron|valero|pemex|fuel|gas", haystack):
            return "EXPENSE", "FUEL", "0.92"
        if self.category == "comida" and subtype == "SUPPLIES" and re.search(r"uline|packaging|empaque", haystack):
            return "EXPENSE", "PACKAGING", "0.88"
        if self.category == "belleza" and subtype == "INVENTORY" and "beauty" in haystack:
            return "EXPENSE", "BEAUTY_SUPPLIES", "0.85"
        return kind, subtype, conf

    def _account_for(self, kind: str, subtype: str) -> dict[str, Any]:
        try:
            return self.accounting.account_by_subtype(subtype)
        except AccountingError:
            return self.accounting.account_by_subtype(coa.CLASSIFICATION_KINDS[kind]["subtype"])

    @staticmethod
    def _suggestion(kind: str, account: dict[str, Any], confidence: str, reason: str) -> dict[str, Any]:
        conf = D(confidence)
        return {
            "kind": kind,
            "kind_label": coa.CLASSIFICATION_KINDS[kind]["label"],
            "account_id": account["account_id"],
            "account_name": account["account_name"],
            "confidence": conf,
            "reason": reason,
            "requires_user_confirmation": conf < AUTO_POST_CONFIDENCE,
        }

    def _auto_classify_and_post(self, tx: dict[str, Any]) -> dict[str, Any]:
        suggestion = self.suggest(tx)
        entry = self._post_for(tx, suggestion["kind"], suggestion["account_id"])
        status = "NEEDS_REVIEW" if suggestion["requires_user_confirmation"] else "CLASSIFIED"
        self.repo.update(
            "card_transactions",
            tx["transaction_id"],
            {
                "classification_status": status,
                "classification_kind": suggestion["kind"],
                "classified_account_id": suggestion["account_id"],
                "confidence": q4(suggestion["confidence"]),
                "classification_reason": suggestion["reason"],
                "journal_entry_id": entry["entry_id"],
            },
        )
        return {**tx, "classification_status": status, "journal_entry_id": entry["entry_id"]}

    def _post_for(self, tx: dict[str, Any], kind: str, account_id: str) -> dict[str, Any]:
        card = self.accounting.account_by_subtype("CARD")
        amount = D(tx["amount"])
        target = self.accounting.account(account_id)
        if tx["direction"] == "CREDIT":
            # Pago a la tarjeta desde el banco (o devolución de un comercio).
            source = self.accounting.account_by_subtype("BANK") if kind == "CARD_PAYMENT" else target
            lines = [Line(card["account_id"], debit=amount, memo=tx["merchant"]), Line(source["account_id"], credit=amount)]
            desc = f"Pago de tarjeta: {tx['merchant']}" if kind == "CARD_PAYMENT" else f"Abono: {tx['merchant']}"
        else:
            lines = [Line(target["account_id"], debit=amount, memo=tx["merchant"]), Line(card["account_id"], credit=amount)]
            desc = f"Compra con tarjeta: {tx['merchant']}"
        self.repo.insert(
            "business_events",
            {
                "event_id": new_id(),
                "event_type": "PURCHASE_CAPTURED" if tx["direction"] == "DEBIT" else "CARD_CREDIT",
                "source_type": "CARD_TRANSACTION",
                "source_id": tx["transaction_id"],
                "payload": json.dumps({"merchant": tx["merchant"], "amount": str(q2(amount)), "kind": kind}),
                "journal_entry_id": None,
                "created_at": now_iso(),
            },
        )
        return self.accounting.post_entry(
            entry_date=iso_date(tx["occurred_at"]),
            description=desc,
            source_type="PURCHASE_CAPTURED",
            source_id=tx["transaction_id"],
            lines=lines,
        )

    def classify(self, transaction_id: str, kind: str, account_id: str | None = None, remember: bool = True) -> dict[str, Any]:
        """El dueño confirma o corrige. Si cambia la cuenta, se publica una
        reclasificación (mover el cargo de la cuenta vieja a la nueva)."""
        if kind not in coa.CLASSIFICATION_KINDS:
            raise ValueError("clasificación desconocida")
        tx = self.get_transaction(transaction_id)
        target = self.accounting.account(account_id) if account_id else self._account_for(kind, coa.CLASSIFICATION_KINDS[kind]["subtype"])
        with self.repo.transaction():
            if tx["journal_entry_id"] is None:
                entry = self._post_for(tx, kind, target["account_id"])
                entry_id = entry["entry_id"]
            elif tx["classified_account_id"] != target["account_id"] and tx["direction"] == "DEBIT":
                old = self.accounting.account(tx["classified_account_id"])
                amount = D(tx["amount"])
                reclass = self.accounting.post_entry(
                    entry_date=iso_date(tx["occurred_at"]),
                    description=f"Reclasificación: {tx['merchant']} ({old['account_name']} → {target['account_name']})",
                    source_type="RECLASSIFICATION",
                    source_id=f"{tx['transaction_id']}:{new_id()[:8]}",
                    lines=[Line(target["account_id"], debit=amount, memo=tx["merchant"]), Line(old["account_id"], credit=amount)],
                )
                entry_id = reclass["entry_id"]
            else:
                entry_id = tx["journal_entry_id"]
            self.repo.update(
                "card_transactions",
                transaction_id,
                {
                    "classification_status": "CLASSIFIED",
                    "classification_kind": kind,
                    "classified_account_id": target["account_id"],
                    "confidence": D("1"),
                    "classification_reason": "Confirmado por el dueño",
                    "journal_entry_id": entry_id,
                },
            )
            if remember and tx["direction"] == "DEBIT":
                self._remember(tx["merchant"], kind, target["account_id"])
        return self.get_transaction(transaction_id)

    def _remember(self, merchant: str, kind: str, account_id: str) -> None:
        pattern = merchant.strip().lower()[:80]
        if not pattern:
            return
        existing = self.repo.find_one("merchant_rules", "merchant_pattern = :p", {"p": pattern})
        if existing:
            self.repo.update("merchant_rules", existing["rule_id"], {"classification_kind": kind, "account_id": account_id})
        else:
            self.repo.insert(
                "merchant_rules",
                {"rule_id": new_id(), "merchant_pattern": pattern, "classification_kind": kind, "account_id": account_id, "created_at": now_iso()},
            )

    # ------------------------------------------------------------ tickets --

    def _sample_receipt(self, merchant: str) -> list[dict[str, Any]] | None:
        key = merchant.strip().lower()
        for name, items in SAMPLE_RECEIPTS.items():
            if name in key:
                return items
        return None

    def sample_receipt(self, transaction_id: str) -> list[dict[str, Any]]:
        """Artículos que un OCR habría extraído, ya emparejados con el
        inventario del negocio (o marcados como nuevos) y escalados para que
        cuadren con el monto de la transacción."""
        tx = self.get_transaction(transaction_id)
        template = self._sample_receipt(tx["merchant"]) or []
        if not template:
            return []
        raw_total = sum((D(i["quantity"]) * D(i["unit_cost"]) for i in template), ZERO)
        scale = (D(tx["amount"]) / raw_total) if raw_total else D("1")
        inventory = self.inventory.list_items(include_inactive=True)
        out = []
        for i in template:
            match = next((it for it in inventory if i["match"] in it["name"].lower()), None)
            unit_cost = q4(D(i["unit_cost"]) * scale)
            out.append(
                {
                    "description": i["description"],
                    "quantity": D(i["quantity"]),
                    "unit": i["unit"],
                    "unit_cost": unit_cost,
                    "total_cost": q2(D(i["quantity"]) * unit_cost),
                    "inventory_item_id": match["inventory_item_id"] if match else None,
                    "inventory_item_name": match["name"] if match else None,
                    "suggested_name": i["match"].capitalize(),
                }
            )
        return out

    def attach_receipt(self, transaction_id: str, items: list[dict[str, Any]], source: str = "sample") -> dict[str, Any]:
        """Enriquece la compra: crea el ticket, da entrada al inventario de los
        artículos emparejados (creando insumos nuevos si se pide) y, si la
        compra no estaba clasificada como inventario, la reclasifica."""
        tx = self.get_transaction(transaction_id)
        if tx["receipt_id"]:
            raise ValueError("esta compra ya tiene ticket")
        if tx["direction"] != "DEBIT":
            raise ValueError("sólo las compras llevan ticket")
        with self.repo.transaction():
            receipt = {
                "receipt_id": new_id(),
                "transaction_id": transaction_id,
                "merchant": tx["merchant"],
                "total": ZERO,
                "source": source,
                "received_at": tx["occurred_at"],
                "created_at": now_iso(),
            }
            self.repo.insert("receipts", receipt)
            total = ZERO
            stocked = ZERO
            for raw in items:
                quantity, unit_cost = D(raw.get("quantity", 0)), D(raw.get("unit_cost", 0))
                if quantity <= 0:
                    continue
                inv_id = raw.get("inventory_item_id")
                if not inv_id and raw.get("create_inventory_item"):
                    created = self.inventory.create_item(
                        name=raw.get("suggested_name") or raw.get("description") or "Insumo",
                        unit_of_measure=raw.get("unit") or "unidad",
                    )
                    inv_id = created["inventory_item_id"]
                line_total = q4(quantity * unit_cost)
                total += line_total
                self.repo.insert(
                    "receipt_items",
                    {
                        "receipt_item_id": new_id(),
                        "receipt_id": receipt["receipt_id"],
                        "description": str(raw.get("description") or "")[:200],
                        "quantity": q4(quantity),
                        "unit": str(raw.get("unit") or "")[:24],
                        "unit_cost": q4(unit_cost),
                        "total_cost": line_total,
                        "inventory_item_id": inv_id,
                    },
                )
                if inv_id:
                    self.inventory.receive(
                        inv_id,
                        quantity,
                        unit_cost,
                        source_type="RECEIPT",
                        source_id=receipt["receipt_id"],
                        note=f"Ticket {tx['merchant']}",
                        occurred_at=tx["occurred_at"],
                    )
                    stocked += line_total
            self.repo.update("receipts", receipt["receipt_id"], {"total": q4(total)})
            self.repo.update("card_transactions", transaction_id, {"receipt_id": receipt["receipt_id"]})
            # Con artículos en inventario, la compra ES inventario: si estaba en
            # otra cuenta, se reclasifica (con su asiento de reclasificación).
            inv_account = self.accounting.account_by_subtype("INVENTORY")
            if stocked > 0 and tx["classified_account_id"] != inv_account["account_id"]:
                self.classify(transaction_id, "INVENTORY", inv_account["account_id"], remember=True)
            elif tx["classification_status"] != "CLASSIFIED":
                self.repo.update("card_transactions", transaction_id, {"classification_status": "CLASSIFIED", "confidence": D("1")})
        return self.get_transaction(transaction_id)

    def _receipt_with_items(self, receipt_id: str) -> dict[str, Any] | None:
        receipt = self.repo.get("receipts", receipt_id)
        if not receipt:
            return None
        receipt["items"] = self.repo.find("receipt_items", "receipt_id = :r", {"r": receipt_id})
        return receipt

    # ------------------------------------------------------------ reportes --

    def spending(self, start: str | None, end: str | None) -> dict[str, Any]:
        where, params = ["business_id = :business_id", "direction = 'DEBIT'"], {}
        if start:
            where.append("occurred_at >= :start")
            params["start"] = iso_date(start)
        if end:
            where.append("occurred_at <= :end")
            params["end"] = iso_date(end) + "T23:59:59"
        rows = self.repo.query(f"SELECT * FROM card_transactions WHERE {' AND '.join(where)}", params)
        by_merchant: dict[str, Decimal] = {}
        by_kind: dict[str, Decimal] = {}
        by_account: dict[str, dict[str, Any]] = {}
        for r in rows:
            amt = D(r["amount"])
            by_merchant[r["merchant"]] = by_merchant.get(r["merchant"], ZERO) + amt
            kind = r["classification_kind"] or "PENDING"
            by_kind[kind] = by_kind.get(kind, ZERO) + amt
            if r["classified_account_id"]:
                try:
                    acc = self.accounting.account(r["classified_account_id"])
                except AccountingError:
                    acc = None
                if acc is None:
                    continue
                slot = by_account.setdefault(acc["account_id"], {"account_name": acc["account_name"], "account_subtype": acc["account_subtype"], "amount": ZERO})
                slot["amount"] += amt
        return {
            "start": start,
            "end": end,
            "transaction_count": len(rows),
            "total": sum((D(r["amount"]) for r in rows), ZERO),
            "by_merchant": sorted(({"merchant": m, "amount": a} for m, a in by_merchant.items()), key=lambda x: x["amount"], reverse=True),
            "by_kind": [{"kind": k, "label": coa.CLASSIFICATION_KINDS.get(k, {}).get("label", k), "amount": a} for k, a in by_kind.items()],
            "by_account": sorted(by_account.values(), key=lambda x: x["amount"], reverse=True),
            "pending_review": sum(1 for r in rows if r["classification_status"] == "NEEDS_REVIEW"),
        }
