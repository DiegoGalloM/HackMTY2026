"""
Productos y servicios vendibles, con su receta (lista de materiales).

Un modelo para los dos: un producto normalmente consume insumos y un servicio
normalmente no, pero un servicio también puede llevar receta (tinte + guantes)
y un producto puede no llevar (mercancía revendida sin insumos capturados).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.finance.common import ZERO, D, new_id, now_iso, q4
from app.finance.inventory import InventoryService
from app.finance.repo import Repo


class CatalogError(ValueError):
    pass


class CatalogService:
    def __init__(self, repo: Repo, inventory: InventoryService):
        self.repo = repo
        self.inventory = inventory

    def list_items(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        where = "" if include_inactive else "is_active = :active"
        items = self.repo.find("sellable_items", where, {"active": True}, order_by="name")
        components = self._components_for([i["item_id"] for i in items])
        inv = {i["inventory_item_id"]: i for i in self.inventory.list_items(include_inactive=True)}
        for it in items:
            self._enrich(it, components.get(it["item_id"], []), inv)
        return items

    def get_item(self, item_id: str) -> dict[str, Any]:
        item = self.repo.get("sellable_items", item_id)
        if not item:
            raise CatalogError("ese producto o servicio no existe")
        inv = {i["inventory_item_id"]: i for i in self.inventory.list_items(include_inactive=True)}
        self._enrich(item, self._components_for([item_id]).get(item_id, []), inv)
        return item

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        return self.repo.find_one("sellable_items", "LOWER(name) = :n", {"n": name.strip().lower()})

    def _components_for(self, item_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not item_ids:
            return {}
        params = {f"i{j}": iid for j, iid in enumerate(item_ids)}
        placeholders = ", ".join(f":i{j}" for j in range(len(item_ids)))
        rows = self.repo.query(
            f"SELECT * FROM item_components WHERE business_id = :business_id AND item_id IN ({placeholders})",
            params,
        )
        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(r["item_id"], []).append(r)
        return out

    def _enrich(self, item: dict[str, Any], components: list[dict[str, Any]], inv: dict[str, dict[str, Any]]) -> None:
        """Agrega receta con nombres, costo unitario estimado y cuántas
        unidades se pueden producir con lo que hay."""
        unit_cost = ZERO
        capacity: Decimal | None = None
        enriched = []
        for c in components:
            ing = inv.get(c["inventory_item_id"])
            if not ing:
                continue
            per_unit = D(c["quantity_per_unit"])
            unit_cost += per_unit * D(ing["average_unit_cost"])
            if per_unit > 0:
                possible = (D(ing["quantity_on_hand"]) / per_unit).to_integral_value(rounding="ROUND_FLOOR")
                capacity = possible if capacity is None else min(capacity, possible)
            enriched.append(
                {
                    **c,
                    "inventory_item_name": ing["name"],
                    "unit_of_measure": ing["unit_of_measure"],
                    "average_unit_cost": D(ing["average_unit_cost"]),
                    "quantity_on_hand": D(ing["quantity_on_hand"]),
                }
            )
        item["components"] = enriched
        item["estimated_unit_cost"] = q4(unit_cost)
        price = D(item["selling_price"])
        item["estimated_margin"] = q4(price - unit_cost)
        item["estimated_margin_pct"] = q4((price - unit_cost) / price * 100) if price > 0 else None
        item["producible_units"] = int(max(capacity, ZERO)) if capacity is not None else None

    def create_item(
        self,
        *,
        name: str,
        item_type: str,
        selling_price: Decimal | float,
        description: str = "",
        tax_rate: Decimal | float = 0,
        emoji: str = "",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        item_type = item_type.upper()
        if item_type not in {"PRODUCT", "SERVICE"}:
            raise CatalogError("item_type debe ser PRODUCT o SERVICE")
        if D(selling_price) < 0:
            raise CatalogError("el precio no puede ser negativo")
        ts = now_iso()
        item = {
            "item_id": new_id(),
            "name": name.strip()[:120],
            "description": (description or "")[:500],
            "item_type": item_type,
            "selling_price": q4(selling_price),
            "tax_rate": q4(tax_rate or 0),
            "emoji": (emoji or "")[:8],
            "is_active": True,
            "created_at": ts,
            "updated_at": ts,
        }
        with self.repo.transaction():
            self.repo.insert("sellable_items", item)
            self.set_components(item["item_id"], components or [])
        return self.get_item(item["item_id"])

    def update_item(self, item_id: str, components: list[dict[str, Any]] | None = None, **fields: Any) -> dict[str, Any]:
        allowed = {
            k: v
            for k, v in fields.items()
            if k in {"name", "description", "selling_price", "tax_rate", "emoji", "is_active", "item_type"} and v is not None
        }
        for money_field in ("selling_price", "tax_rate"):
            if money_field in allowed:
                allowed[money_field] = q4(allowed[money_field])
        allowed["updated_at"] = now_iso()
        with self.repo.transaction():
            self.repo.update("sellable_items", item_id, allowed)
            if components is not None:
                self.set_components(item_id, components)
        return self.get_item(item_id)

    def set_components(self, item_id: str, components: list[dict[str, Any]]) -> None:
        """Reemplaza la receta completa. Cada componente: inventory_item_id +
        quantity_per_unit."""
        self.repo.db.execute(
            "DELETE FROM item_components WHERE business_id = :business_id AND item_id = :item_id",
            {"business_id": self.repo.business_id, "item_id": item_id},
        )
        for c in components:
            inv_id = c.get("inventory_item_id")
            per_unit = D(c.get("quantity_per_unit", 0))
            if not inv_id or per_unit <= 0:
                continue
            self.inventory.get_item(inv_id)  # valida que sea de este negocio
            self.repo.insert(
                "item_components",
                {
                    "component_id": new_id(),
                    "item_id": item_id,
                    "inventory_item_id": inv_id,
                    "quantity_per_unit": q4(per_unit),
                },
            )
