"""
Ventas: orden -> QR (token opaco) -> pago confirmado -> consecuencias.

Nada financiero pasa al crear la orden ni al escanear el QR. Sólo
`complete_payment()` (con un PaymentEvent SUCCEEDED) marca la orden pagada,
registra el pago, consume inventario según la receta, reconoce ingreso,
impuesto y costo de ventas, y deja el evento de negocio. Todo en UNA
transacción y de forma idempotente: el mismo pago dos veces no duplica nada.
"""

from __future__ import annotations

import json
import secrets
from decimal import Decimal
from typing import Any

from app.finance.accounting import AccountingService, Line
from app.finance.catalog import CatalogService
from app.finance.common import ZERO, D, iso_date, new_id, now_iso, q2, q4, safe_div
from app.finance.inventory import InventoryService
from app.finance.payments import PaymentEvent
from app.finance.repo import Repo


class SalesError(ValueError):
    pass


class PaymentMismatch(SalesError):
    pass


class SalesService:
    def __init__(self, repo: Repo, accounting: AccountingService, inventory: InventoryService, catalog: CatalogService):
        self.repo = repo
        self.accounting = accounting
        self.inventory = inventory
        self.catalog = catalog
        self._paid_cache: tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]] | None = None

    # ------------------------------------------------------------ órdenes --

    def create_order(
        self,
        lines: list[dict[str, Any]],
        note: str = "",
        currency: str = "USD",
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if not lines:
            raise SalesError("la orden necesita al menos un producto o servicio")
        ts = created_at or now_iso()
        order_lines, subtotal, tax_total = [], ZERO, ZERO
        catalog = {it["item_id"]: it for it in self.catalog.list_items(include_inactive=True)}
        for raw in lines:
            item = catalog.get(raw["item_id"])
            if item is None:
                raise SalesError("ese producto o servicio no existe")
            if not item["is_active"]:
                raise SalesError(f"{item['name']} está inactivo")
            quantity = D(raw.get("quantity", 1))
            if quantity <= 0:
                raise SalesError("la cantidad debe ser mayor a cero")
            unit_price = D(item["selling_price"])
            line_subtotal = q2(unit_price * quantity)
            line_tax = q2(line_subtotal * D(item["tax_rate"]))
            subtotal += line_subtotal
            tax_total += line_tax
            order_lines.append(
                {
                    "order_line_id": new_id(),
                    "item_id": item["item_id"],
                    "item_name": item["name"],
                    "item_type": item["item_type"],
                    "quantity": q4(quantity),
                    "unit_price": q4(unit_price),
                    "tax_rate": q4(item["tax_rate"]),
                    "line_subtotal": line_subtotal,
                    "line_tax": line_tax,
                    "line_total": line_subtotal + line_tax,
                    "unit_cost": None,
                }
            )
        order = {
            "order_id": new_id(),
            "order_number": self.repo.next_number("sales_orders", "order_number"),
            "status": "AWAITING_PAYMENT",
            "subtotal": subtotal,
            "tax_total": tax_total,
            "total": subtotal + tax_total,
            "currency": currency,
            "customer_id": None,
            # 32 bytes de aleatoriedad: el token es lo único que viaja en el QR
            # y no revela ni el negocio ni el consecutivo de la orden.
            "checkout_token": secrets.token_urlsafe(32),
            "note": (note or "")[:300],
            "created_at": ts,
            "paid_at": None,
        }
        with self.repo.transaction():
            self.repo.insert("sales_orders", order)
            self.repo.insert_many("order_lines", [{**ln, "order_id": order["order_id"]} for ln in order_lines])
        return {**order, "business_id": self.repo.business_id, "lines": order_lines, "payment": None, "customer": None}

    def get_order(self, order_id: str) -> dict[str, Any]:
        order = self.repo.get("sales_orders", order_id)
        if not order:
            raise SalesError("esa orden no existe")
        return self._hydrate(order)

    def _hydrate(self, order: dict[str, Any]) -> dict[str, Any]:
        return self._hydrate_many([order])[0]

    def _hydrate_many(self, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Líneas, pago y cliente de varias órdenes en 3 consultas, no 3 por orden."""
        if not orders:
            return orders
        ids = [o["order_id"] for o in orders]
        lines_by_order: dict[str, list[dict[str, Any]]] = {}
        for ln in sorted(self._lines_for(ids), key=lambda x: x["item_name"] or ""):
            lines_by_order.setdefault(ln["order_id"], []).append(ln)
        payments: dict[str, dict[str, Any]] = {}
        for p in self._in_query("payments", "order_id", ids, extra="AND status = 'SUCCEEDED'"):
            payments.setdefault(p["order_id"], p)
        customer_ids = [o["customer_id"] for o in orders if o.get("customer_id")]
        customers = {c["customer_id"]: c for c in self._in_query("customers", "customer_id", customer_ids)}
        for o in orders:
            o["lines"] = lines_by_order.get(o["order_id"], [])
            o["payment"] = payments.get(o["order_id"])
            o["customer"] = customers.get(o["customer_id"]) if o.get("customer_id") else None
        return orders

    def _in_query(self, table: str, column: str, values: list[str], extra: str = "") -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i in range(0, len(values), 200):
            chunk = values[i : i + 200]
            if not chunk:
                continue
            params = {f"v{j}": v for j, v in enumerate(chunk)}
            placeholders = ", ".join(f":v{j}" for j in range(len(chunk)))
            out.extend(
                self.repo.query(
                    f"SELECT * FROM {table} WHERE business_id = :business_id AND {column} IN ({placeholders}) {extra}",
                    params,
                )
            )
        return out

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        order = self.get_order(order_id)
        if order["status"] == "PAID":
            raise SalesError("una orden pagada no se cancela: registra una devolución")
        self.repo.update("sales_orders", order_id, {"status": "CANCELLED"})
        return self.get_order(order_id)

    def list_orders(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        where, params = "", {}
        if status:
            where, params = "status = :s", {"s": status}
        orders = self.repo.find("sales_orders", where, params, order_by="created_at DESC", limit=limit)
        return self._hydrate_many(orders)

    # -------------------------------------------------------- checkout --

    def find_order_by_token(self, token: str) -> dict[str, Any] | None:
        order = self.repo.find_one("sales_orders", "checkout_token = :t", {"t": token})
        return self._hydrate(order) if order else None

    # ------------------------------------------------ pago autoritativo --

    def complete_payment(self, event: PaymentEvent) -> dict[str, Any]:
        """La única puerta hacia las consecuencias financieras de una venta."""
        order = self.get_order(event.order_id)

        # Idempotencia 1: el proveedor reintentó el mismo evento.
        existing = self.repo.find_one("payments", "provider_ref = :r", {"r": event.provider_ref})
        if existing:
            return self._result(order, existing, already=True)
        # Idempotencia 2: la orden ya se pagó por otra vía.
        if order["status"] == "PAID":
            return self._result(order, order["payment"], already=True)
        if order["status"] == "CANCELLED":
            raise SalesError("la orden está cancelada")

        if event.status != "SUCCEEDED":
            payment = self._payment_row(event, order, status="FAILED")
            self.repo.insert("payments", payment)
            return {"order": order, "payment": payment, "status": "FAILED", "already_processed": False}

        if q2(event.amount) != q2(order["total"]):
            raise PaymentMismatch(
                f"el pago ({event.amount}) no coincide con el total de la orden ({order['total']})"
            )

        occurred = event.occurred_at or now_iso()
        with self.repo.transaction():
            customer_id = self._resolve_customer(event)
            payment = self._payment_row(event, order, status="SUCCEEDED", customer_id=customer_id, confirmed_at=occurred)
            self.repo.insert("payments", payment)

            # Inventario: cada línea consume su receta al costo promedio. Todas
            # las salidas de la orden van juntas (una lectura, una inserción).
            catalog = {it["item_id"]: it for it in self.catalog.list_items(include_inactive=True)}
            requests: list[tuple[str, Decimal, str]] = []
            owners: list[dict[str, Any]] = []
            for line in order["lines"]:
                item = catalog.get(line["item_id"])
                if item is None:
                    raise SalesError(f"el producto de la línea {line['item_name']} ya no existe")
                for comp in item["components"]:
                    needed = D(comp["quantity_per_unit"]) * D(line["quantity"])
                    requests.append((comp["inventory_item_id"], needed, f"{line['item_name']} × {q4(line['quantity']).normalize()}"))
                    owners.append(line)
            movements = self.inventory.consume_many(requests, source_type="SALE", source_id=order["order_id"], occurred_at=occurred)
            total_cogs = ZERO
            line_costs: dict[str, Decimal] = {}
            for line, mv in zip(owners, movements, strict=True):
                cost = -D(mv["total_cost"])
                line_costs[line["order_line_id"]] = line_costs.get(line["order_line_id"], ZERO) + cost
                total_cogs += cost
            for line in order["lines"]:
                unit_cost = safe_div(line_costs.get(line["order_line_id"], ZERO), line["quantity"]) or ZERO
                if unit_cost:
                    self.repo.update("order_lines", line["order_line_id"], {"unit_cost": q4(unit_cost)})

            # Contabilidad: ingreso + impuesto contra el banco, y costo contra inventario.
            bank = self.accounting.account_by_subtype("BANK")
            product_rev = self.accounting.account_by_subtype("PRODUCT_REVENUE")
            service_rev = self.accounting.account_by_subtype("SERVICE_REVENUE")
            tax_payable = self.accounting.account_by_subtype("TAX_PAYABLE")
            product_sub = sum((D(ln["line_subtotal"]) for ln in order["lines"] if ln["item_type"] == "PRODUCT"), ZERO)
            service_sub = sum((D(ln["line_subtotal"]) for ln in order["lines"] if ln["item_type"] != "PRODUCT"), ZERO)
            # allow_duplicate_source: la idempotencia de la venta ya la garantiza
            # el estado de la orden y la referencia del pago (arriba); así se
            # ahorra la búsqueda del asiento previo dentro de la transacción.
            sale_entry = self.accounting.post_entry(
                entry_date=iso_date(occurred),
                description=f"Venta #{order['order_number']} (QR)",
                source_type="SALE_COMPLETED",
                source_id=order["order_id"],
                allow_duplicate_source=True,
                lines=[
                    Line(bank["account_id"], debit=D(order["total"]), memo=f"Pago {event.provider} {event.provider_ref[-6:]}"),
                    Line(product_rev["account_id"], credit=product_sub, memo="Productos"),
                    Line(service_rev["account_id"], credit=service_sub, memo="Servicios"),
                    Line(tax_payable["account_id"], credit=D(order["tax_total"]), memo="Impuesto sobre ventas"),
                ],
            )
            cogs_entry = None
            if total_cogs > 0:
                cogs = self.accounting.account_by_subtype("COGS")
                inv = self.accounting.account_by_subtype("INVENTORY")
                cogs_entry = self.accounting.post_entry(
                    entry_date=iso_date(occurred),
                    description=f"Costo de venta #{order['order_number']}",
                    source_type="SALE_COGS",
                    source_id=order["order_id"],
                    allow_duplicate_source=True,
                    lines=[Line(cogs["account_id"], debit=total_cogs), Line(inv["account_id"], credit=total_cogs)],
                )

            self.repo.update(
                "sales_orders",
                order["order_id"],
                {"status": "PAID", "paid_at": occurred, "customer_id": customer_id},
            )
            self.repo.insert(
                "business_events",
                {
                    "event_id": new_id(),
                    "event_type": "SALE_COMPLETED",
                    "source_type": "PAYMENT",
                    "source_id": payment["payment_id"],
                    "payload": json.dumps(
                        {
                            "order_id": order["order_id"],
                            "order_number": order["order_number"],
                            "total": str(q2(order["total"])),
                            "cogs": str(q2(total_cogs)),
                            "movements": [m["movement_id"] for m in movements],
                            "cogs_entry_id": cogs_entry["entry_id"] if cogs_entry else None,
                        }
                    ),
                    "journal_entry_id": sale_entry["entry_id"],
                    "created_at": now_iso(),
                },
            )

        self._paid_cache = None  # hay una orden pagada nueva
        # La orden ya está en memoria: se actualiza aquí en vez de releerla.
        for line in order["lines"]:
            if line["order_line_id"] in line_costs:
                line["unit_cost"] = q4(safe_div(line_costs[line["order_line_id"]], line["quantity"]) or ZERO)
        order.update({"status": "PAID", "paid_at": occurred, "customer_id": customer_id, "payment": payment})
        result = self._result(order, payment, already=False)
        result.update(
            {
                "cogs": total_cogs,
                "gross_profit": D(order["subtotal"]) - total_cogs,
                "inventory_movements": movements,
                "journal_entries": [e for e in (sale_entry, cogs_entry) if e],
            }
        )
        return result

    def _payment_row(
        self, event: PaymentEvent, order: dict[str, Any], *, status: str, customer_id: str | None = None, confirmed_at: str | None = None
    ) -> dict[str, Any]:
        return {
            "payment_id": new_id(),
            "order_id": order["order_id"],
            "provider": event.provider,
            "provider_ref": event.provider_ref,
            "amount": q4(event.amount),
            "currency": event.currency,
            "method": event.method,
            "status": status,
            "card_last4": event.card_last4,
            "customer_id": customer_id,
            "created_at": now_iso(),
            "confirmed_at": confirmed_at,
        }

    def _resolve_customer(self, event: PaymentEvent) -> str | None:
        """Cliente conocido, nuevo o anónimo. Sólo con datos que el cliente dio
        voluntariamente en el checkout; nunca es obligatorio."""
        email = (event.customer_email or "").strip().lower()
        phone = (event.customer_phone or "").strip()
        name = (event.customer_name or "").strip()
        if not (email or phone or name):
            return None
        existing = None
        if email:
            existing = self.repo.find_one("customers", "LOWER(email) = :e", {"e": email})
        if not existing and phone:
            existing = self.repo.find_one("customers", "phone = :p", {"p": phone})
        if existing:
            return existing["customer_id"]
        customer = {
            "customer_id": new_id(),
            "display_name": name[:120] or (email.split("@")[0] if email else "Cliente"),
            "email": email or None,
            "phone": phone or None,
            "created_at": now_iso(),
        }
        self.repo.insert("customers", customer)
        return customer["customer_id"]

    @staticmethod
    def _result(order: dict[str, Any], payment: dict[str, Any] | None, *, already: bool) -> dict[str, Any]:
        return {"order": order, "payment": payment, "status": order["status"], "already_processed": already}

    # ----------------------------------------------------------- reportes --

    def _paid_orders(self) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        """Todas las órdenes pagadas y sus líneas, UNA vez por request; los
        resúmenes por periodo se filtran en Python (cientos de filas)."""
        if self._paid_cache is None:
            orders = self.repo.find("sales_orders", "status = 'PAID'", order_by="paid_at")
            lines: dict[str, list[dict[str, Any]]] = {}
            for ln in self._lines_for([o["order_id"] for o in orders]):
                lines.setdefault(ln["order_id"], []).append(ln)
            self._paid_cache = (orders, lines)
        return self._paid_cache

    def sales_summary(self, start: str | None, end: str | None) -> dict[str, Any]:
        s = iso_date(start) if start else None
        e = iso_date(end) + "T23:59:59" if end else None
        all_orders, lines_by_order = self._paid_orders()
        orders = [o for o in all_orders if (not s or str(o["paid_at"]) >= s) and (not e or str(o["paid_at"]) <= e)]
        lines = [ln for o in orders for ln in lines_by_order.get(o["order_id"], [])]
        revenue = sum((D(o["subtotal"]) for o in orders), ZERO)
        tax = sum((D(o["tax_total"]) for o in orders), ZERO)
        collected = sum((D(o["total"]) for o in orders), ZERO)
        cogs = sum((D(ln["unit_cost"] or 0) * D(ln["quantity"]) for ln in lines), ZERO)
        by_item: dict[str, dict[str, Any]] = {}
        for ln in lines:
            slot = by_item.setdefault(
                ln["item_id"], {"item_id": ln["item_id"], "name": ln["item_name"], "units": ZERO, "revenue": ZERO, "cogs": ZERO}
            )
            slot["units"] += D(ln["quantity"])
            slot["revenue"] += D(ln["line_subtotal"])
            slot["cogs"] += D(ln["unit_cost"] or 0) * D(ln["quantity"])
        for slot in by_item.values():
            slot["gross_profit"] = slot["revenue"] - slot["cogs"]
        top = sorted(by_item.values(), key=lambda s: s["gross_profit"], reverse=True)
        return {
            "start": start,
            "end": end,
            "order_count": len(orders),
            "units_sold": sum((D(ln["quantity"]) for ln in lines), ZERO),
            "revenue": revenue,
            "tax_collected": tax,
            "cash_collected": collected,
            "cogs": cogs,
            "gross_profit": revenue - cogs,
            "gross_margin_pct": (safe_div(revenue - cogs, revenue) or ZERO) * 100 if revenue else None,
            "average_ticket": safe_div(revenue, len(orders)),
            "by_item": top,
        }

    def _lines_for(self, order_ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i in range(0, len(order_ids), 200):
            chunk = order_ids[i : i + 200]
            if not chunk:
                continue
            params = {f"o{j}": oid for j, oid in enumerate(chunk)}
            placeholders = ", ".join(f":o{j}" for j in range(len(chunk)))
            out.extend(
                self.repo.query(
                    f"SELECT * FROM order_lines WHERE business_id = :business_id AND order_id IN ({placeholders})",
                    params,
                )
            )
        return out

    def sales_by_day(self, start: str, end: str) -> list[dict[str, Any]]:
        s, e = iso_date(start), iso_date(end) + "T23:59:59"
        days: dict[str, dict[str, Any]] = {}
        for o in self._paid_orders()[0]:
            paid = str(o["paid_at"])
            if paid < s or paid > e:
                continue
            slot = days.setdefault(paid[:10], {"day": paid[:10], "orders": 0, "revenue": ZERO})
            slot["orders"] += 1
            slot["revenue"] += D(o["subtotal"])
        return [days[k] for k in sorted(days)]

    def customers_summary(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.repo.query(
            "SELECT c.customer_id, c.display_name, c.email, c.phone, "
            "COUNT(o.order_id) AS purchase_count, COALESCE(SUM(o.total), 0) AS lifetime_revenue, "
            "MIN(o.paid_at) AS first_purchase, MAX(o.paid_at) AS last_purchase "
            "FROM customers c LEFT JOIN sales_orders o "
            "ON o.customer_id = c.customer_id AND o.business_id = c.business_id AND o.status = 'PAID' "
            "WHERE c.business_id = :business_id "
            "GROUP BY c.customer_id, c.display_name, c.email, c.phone ORDER BY lifetime_revenue DESC",
            {},
        )
        for r in rows:
            r["purchase_count"] = int(r["purchase_count"] or 0)
            r["lifetime_revenue"] = D(r["lifetime_revenue"])
            r["average_order_value"] = safe_div(r["lifetime_revenue"], r["purchase_count"])
        return rows[:limit]
