"""
Inventario con costo promedio ponderado y bitácora de movimientos.

Nunca se cambia quantity_on_hand sin dejar un inventory_movement: el saldo se
puede reconstruir sumando la bitácora, y cada movimiento apunta al evento que
lo causó (compra, venta, ajuste).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.finance.accounting import AccountingService, Line
from app.finance.common import ZERO, D, new_id, now_iso, q4, safe_div
from app.finance.repo import Repo


class InventoryError(ValueError):
    pass


class InventoryService:
    def __init__(self, repo: Repo, accounting: AccountingService):
        self.repo = repo
        self.accounting = accounting

    # ------------------------------------------------------------ items --

    def list_items(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        where = "" if include_inactive else "is_active = :active"
        items = self.repo.find("inventory_items", where, {"active": True}, order_by="name")
        for it in items:
            it["inventory_value"] = q4(D(it["quantity_on_hand"]) * D(it["average_unit_cost"]))
            it["low_stock"] = self._is_low(it)
        return items

    def get_item(self, inventory_item_id: str) -> dict[str, Any]:
        item = self.repo.get("inventory_items", inventory_item_id)
        if not item:
            raise InventoryError("ese insumo no existe")
        item["inventory_value"] = q4(D(item["quantity_on_hand"]) * D(item["average_unit_cost"]))
        item["low_stock"] = self._is_low(item)
        return item

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        return self.repo.find_one("inventory_items", "LOWER(name) = :n", {"n": name.strip().lower()})

    @staticmethod
    def _is_low(item: dict[str, Any]) -> bool:
        rp = D(item.get("reorder_point"))
        return rp > 0 and D(item["quantity_on_hand"]) <= rp

    def create_item(
        self,
        *,
        name: str,
        unit_of_measure: str,
        reorder_point: Decimal | float | None = None,
        initial_quantity: Decimal | float | None = None,
        initial_unit_cost: Decimal | float | None = None,
        source_type: str = "INITIAL_BALANCE",
        source_id: str | None = None,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        ts = now_iso()
        item = {
            "inventory_item_id": new_id(),
            "name": name.strip()[:120],
            "unit_of_measure": unit_of_measure.strip()[:24] or "unidad",
            "quantity_on_hand": ZERO,
            "average_unit_cost": ZERO,
            "reorder_point": q4(reorder_point or 0),
            "is_active": True,
            "created_at": ts,
            "updated_at": ts,
        }
        with self.repo.transaction():
            self.repo.insert("inventory_items", item)
            if initial_quantity and D(initial_quantity) > 0:
                self.receive(
                    item["inventory_item_id"],
                    D(initial_quantity),
                    D(initial_unit_cost or 0),
                    movement_type="INITIAL",
                    source_type=source_type,
                    source_id=source_id or item["inventory_item_id"],
                    occurred_at=occurred_at,
                    note="Existencia inicial",
                )
                # El inventario inicial lo aporta el dueño: es capital, no gasto.
                cost = q4(D(initial_quantity) * D(initial_unit_cost or 0))
                if cost > 0:
                    inv = self.accounting.account_by_subtype("INVENTORY")
                    cap = self.accounting.account_by_subtype("OWNER_CAPITAL")
                    self.accounting.post_entry(
                        entry_date=(occurred_at or ts)[:10],
                        description=f"Inventario inicial: {item['name']}",
                        source_type="OWNER_CONTRIBUTION",
                        source_id=f"inv-initial-{item['inventory_item_id']}",
                        lines=[Line(inv["account_id"], debit=cost), Line(cap["account_id"], credit=cost)],
                    )
        return self.get_item(item["inventory_item_id"])

    def update_item(self, inventory_item_id: str, **fields: Any) -> dict[str, Any]:
        allowed = {k: v for k, v in fields.items() if k in {"name", "unit_of_measure", "reorder_point", "is_active"} and v is not None}
        if "reorder_point" in allowed:
            allowed["reorder_point"] = q4(allowed["reorder_point"])
        allowed["updated_at"] = now_iso()
        self.repo.update("inventory_items", inventory_item_id, allowed)
        return self.get_item(inventory_item_id)

    # ------------------------------------------------------- movimientos --

    def _record(
        self,
        item: dict[str, Any],
        *,
        movement_type: str,
        quantity_delta: Decimal,
        unit_cost: Decimal,
        source_type: str,
        source_id: str,
        note: str = "",
        occurred_at: str | None = None,
        new_avg: Decimal | None = None,
    ) -> dict[str, Any]:
        new_qty = q4(D(item["quantity_on_hand"]) + quantity_delta)
        movement = {
            "movement_id": new_id(),
            "inventory_item_id": item["inventory_item_id"],
            "movement_type": movement_type,
            "quantity_delta": q4(quantity_delta),
            "unit_cost": q4(unit_cost),
            "total_cost": q4(quantity_delta * unit_cost),
            "quantity_after": new_qty,
            "source_type": source_type,
            "source_id": source_id,
            "note": note[:300],
            "occurred_at": occurred_at or now_iso(),
        }
        self.repo.insert("inventory_movements", movement)
        self.repo.update(
            "inventory_items",
            item["inventory_item_id"],
            {
                "quantity_on_hand": new_qty,
                "average_unit_cost": q4(new_avg if new_avg is not None else D(item["average_unit_cost"])),
                "updated_at": now_iso(),
            },
        )
        return movement

    def receive(
        self,
        inventory_item_id: str,
        quantity: Decimal,
        unit_cost: Decimal,
        *,
        movement_type: str = "PURCHASE",
        source_type: str,
        source_id: str,
        note: str = "",
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        """Entrada: recalcula el costo promedio ponderado.

            nuevo promedio = (qty_actual*costo_actual + qty_nueva*costo_nuevo)
                             / (qty_actual + qty_nueva)
        """
        quantity, unit_cost = D(quantity), D(unit_cost)
        if quantity <= 0:
            raise InventoryError("la cantidad recibida debe ser mayor a cero")
        item = self.get_item(inventory_item_id)
        on_hand = max(D(item["quantity_on_hand"]), ZERO)  # un negativo previo no distorsiona el promedio
        current_value = on_hand * D(item["average_unit_cost"])
        new_avg = safe_div(current_value + quantity * unit_cost, on_hand + quantity) or unit_cost
        with self.repo.transaction():
            return self._record(
                item,
                movement_type=movement_type,
                quantity_delta=quantity,
                unit_cost=unit_cost,
                source_type=source_type,
                source_id=source_id,
                note=note,
                occurred_at=occurred_at,
                new_avg=new_avg,
            )

    def consume(
        self,
        inventory_item_id: str,
        quantity: Decimal,
        *,
        movement_type: str = "SALE_CONSUMPTION",
        source_type: str,
        source_id: str,
        note: str = "",
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        """Salida al costo promedio. Si no alcanza, la venta NO se bloquea (ya
        ocurrió en el mundo real): el saldo queda negativo y se marca para que
        el dueño corrija el conteo."""
        quantity = D(quantity)
        if quantity <= 0:
            raise InventoryError("la cantidad a consumir debe ser mayor a cero")
        item = self.get_item(inventory_item_id)
        shortfall = D(item["quantity_on_hand"]) < quantity
        if shortfall:
            note = (note + " | existencia insuficiente: revisa el conteo").strip(" |")
        with self.repo.transaction():
            return self._record(
                item,
                movement_type=movement_type,
                quantity_delta=-quantity,
                unit_cost=D(item["average_unit_cost"]),
                source_type=source_type,
                source_id=source_id,
                note=note,
                occurred_at=occurred_at,
            )

    def consume_many(
        self,
        requests: list[tuple[str, Decimal, str]],
        *,
        source_type: str,
        source_id: str,
        occurred_at: str | None = None,
    ) -> list[dict[str, Any]]:
        """Varias salidas de una vez (una venta con receta): los insumos se
        leen en UNA consulta, los movimientos se insertan en UNA sentencia y
        sólo queda un UPDATE por insumo. Misma semántica que `consume`."""
        if not requests:
            return []
        items = {it["inventory_item_id"]: it for it in self.list_items(include_inactive=True)}
        # Un mismo insumo puede aparecer en varias líneas: se acumula en orden.
        movements: list[dict[str, Any]] = []
        with self.repo.transaction():
            for inventory_item_id, quantity, note in requests:
                quantity = D(quantity)
                if quantity <= 0:
                    raise InventoryError("la cantidad a consumir debe ser mayor a cero")
                item = items.get(inventory_item_id)
                if item is None:
                    raise InventoryError("ese insumo no existe")
                on_hand = D(item["quantity_on_hand"])
                if on_hand < quantity:
                    note = (note + " | existencia insuficiente: revisa el conteo").strip(" |")
                unit_cost = D(item["average_unit_cost"])
                new_qty = q4(on_hand - quantity)
                movements.append(
                    {
                        "movement_id": new_id(),
                        "inventory_item_id": inventory_item_id,
                        "movement_type": "SALE_CONSUMPTION",
                        "quantity_delta": q4(-quantity),
                        "unit_cost": q4(unit_cost),
                        "total_cost": q4(-quantity * unit_cost),
                        "quantity_after": new_qty,
                        "source_type": source_type,
                        "source_id": source_id,
                        "note": note[:300],
                        "occurred_at": occurred_at or now_iso(),
                    }
                )
                item["quantity_on_hand"] = new_qty
            self.repo.insert_many("inventory_movements", movements)
            touched = sorted({m["inventory_item_id"] for m in movements})
            # Un solo UPDATE para todos los insumos (CASE por id): portable y
            # evita un viaje por insumo.
            params: dict[str, Any] = {"ts": now_iso()}
            cases, ids = [], []
            for j, inventory_item_id in enumerate(touched):
                params[f"i{j}"] = inventory_item_id
                params[f"q{j}"] = q4(items[inventory_item_id]["quantity_on_hand"])
                cases.append(f"WHEN :i{j} THEN :q{j}")
                ids.append(f":i{j}")
            self.repo.db.execute(
                f"UPDATE inventory_items SET quantity_on_hand = CASE inventory_item_id {' '.join(cases)} END, updated_at = :ts "
                f"WHERE business_id = :business_id AND inventory_item_id IN ({', '.join(ids)})",
                {**params, "business_id": self.repo.business_id},
            )
        return movements

    def adjust_count(
        self,
        inventory_item_id: str,
        counted_quantity: Decimal,
        *,
        reason: str = "Conteo físico",
        movement_type: str = "ADJUSTMENT",
        entry_date: str | None = None,
    ) -> dict[str, Any]:
        """Conteo físico: la diferencia va a la bitácora y a un asiento de
        ajuste (merma o sobrante) contra la cuenta de inventario."""
        item = self.get_item(inventory_item_id)
        delta = q4(D(counted_quantity) - D(item["quantity_on_hand"]))
        if delta == 0:
            return {"movement": None, "journal_entry": None, "delta": ZERO}
        avg = D(item["average_unit_cost"])
        cost = q4(abs(delta) * avg)
        with self.repo.transaction():
            movement = self._record(
                item,
                movement_type=movement_type,
                quantity_delta=delta,
                unit_cost=avg,
                source_type="INVENTORY_ADJUSTMENT",
                source_id=new_id(),
                note=reason,
                occurred_at=None,
            )
            entry = None
            if cost > 0:
                inv = self.accounting.account_by_subtype("INVENTORY")
                adj = self.accounting.account_by_subtype("COGS_ADJUSTMENT")
                if delta < 0:
                    lines = [Line(adj["account_id"], debit=cost, memo=item["name"]), Line(inv["account_id"], credit=cost)]
                else:
                    lines = [Line(inv["account_id"], debit=cost, memo=item["name"]), Line(adj["account_id"], credit=cost)]
                entry = self.accounting.post_entry(
                    entry_date=entry_date,
                    description=f"Ajuste de inventario: {item['name']} ({reason})",
                    source_type="INVENTORY_ADJUSTMENT",
                    source_id=movement["movement_id"],
                    lines=lines,
                    is_adjusting=True,
                )
        return {"movement": movement, "journal_entry": entry, "delta": delta}

    def movements(self, inventory_item_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where, params = "", {}
        if inventory_item_id:
            where, params = "inventory_item_id = :i", {"i": inventory_item_id}
        rows = self.repo.find("inventory_movements", where, params, order_by="occurred_at DESC", limit=limit)
        names = {it["inventory_item_id"]: it for it in self.list_items(include_inactive=True)}
        for r in rows:
            it = names.get(r["inventory_item_id"], {})
            r["item_name"] = it.get("name")
            r["unit_of_measure"] = it.get("unit_of_measure")
        return rows

    # ----------------------------------------------------------- resumen --

    def summary(self) -> dict[str, Any]:
        items = self.list_items()
        total_value = sum((D(i["inventory_value"]) for i in items), ZERO)
        low = [i for i in items if i["low_stock"]]
        return {
            "item_count": len(items),
            "total_value": q4(total_value),
            "low_stock_items": low,
            "items": items,
        }
