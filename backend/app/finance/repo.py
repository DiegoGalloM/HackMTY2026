"""
Acceso a tablas del núcleo financiero, SIEMPRE acotado a un negocio.

Cada Repo nace con un business_id y lo mete en todos los INSERT y en el WHERE
de todos los SELECT/UPDATE. Ningún servicio (ni el asistente) puede pedir
filas de otro negocio: no existe un método que reciba business_id como
parámetro.
"""

from __future__ import annotations

from typing import Any

from app.db.base import Database

# Tablas y su llave, para los helpers genéricos.
KEYS = {
    "accounts": "account_id",
    "journal_entries": "entry_id",
    "journal_lines": "line_id",
    "inventory_items": "inventory_item_id",
    "inventory_movements": "movement_id",
    "sellable_items": "item_id",
    "item_components": "component_id",
    "customers": "customer_id",
    "sales_orders": "order_id",
    "order_lines": "order_line_id",
    "payments": "payment_id",
    "card_transactions": "transaction_id",
    "receipts": "receipt_id",
    "receipt_items": "receipt_item_id",
    "merchant_rules": "rule_id",
    "business_events": "event_id",
}


class Repo:
    def __init__(self, db: Database, business_id: str):
        if not business_id:
            raise ValueError("business_id es obligatorio")
        self.db = db
        self.business_id = business_id

    # ----------------------------------------------------------- escritura --

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        row = {**row, "business_id": self.business_id}
        cols = list(row)
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        )
        self.db.execute(sql, row)
        return row

    def insert_many(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Varias filas de la misma forma en una sola sentencia (Snowflake:
        una inserción multi-fila; sqlite: executemany)."""
        if not rows:
            return
        rows = [{**row, "business_id": self.business_id} for row in rows]
        cols = list(rows[0])
        sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        self.db.execute_many(sql, rows)

    def update(self, table: str, key_value: str, values: dict[str, Any]) -> None:
        key = KEYS[table]
        assigns = ", ".join(f"{c} = :{c}" for c in values)
        self.db.execute(
            f"UPDATE {table} SET {assigns} WHERE business_id = :business_id AND {key} = :key_value",
            {**values, "business_id": self.business_id, "key_value": key_value},
        )

    # ------------------------------------------------------------- lectura --

    def get(self, table: str, key_value: str) -> dict[str, Any] | None:
        key = KEYS[table]
        return self.db.row(
            f"SELECT * FROM {table} WHERE business_id = :business_id AND {key} = :key_value",
            {"business_id": self.business_id, "key_value": key_value},
        )

    def find(
        self,
        table: str,
        where: str = "",
        params: dict[str, Any] | None = None,
        order_by: str = "",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table} WHERE business_id = :business_id"
        if where:
            sql += f" AND ({where})"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return self.db.rows(sql, {**(params or {}), "business_id": self.business_id})

    def find_one(self, table: str, where: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self.find(table, where, params, limit=1)
        return rows[0] if rows else None

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """SQL libre del dominio. El SQL DEBE filtrar por :business_id; este
        método lo inyecta para que no se pueda olvidar ni sustituir."""
        if ":business_id" not in sql:
            raise ValueError("toda consulta del dominio debe filtrar por :business_id")
        return self.db.rows(sql, {**(params or {}), "business_id": self.business_id})

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        if ":business_id" not in sql:
            raise ValueError("toda consulta del dominio debe filtrar por :business_id")
        return self.db.scalar(sql, {**(params or {}), "business_id": self.business_id})

    def next_number(self, table: str, column: str) -> int:
        current = self.scalar(
            f"SELECT COALESCE(MAX({column}), 0) FROM {table} WHERE business_id = :business_id"
        )
        return int(current or 0) + 1

    def transaction(self):
        return self.db.transaction()
