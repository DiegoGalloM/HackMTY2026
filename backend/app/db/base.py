"""
Interfaz mínima sobre la que se escribe todo el SQL del núcleo financiero.

Placeholders: el código de dominio escribe `:nombre`. Cada backend lo traduce
al estilo de su driver (sqlite lo entiende tal cual; Snowflake usa %(nombre)s).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"

# Migraciones portables (sqlite + Snowflake). Las 001/002 son sólo de Snowflake
# (warehouse, VARIANT, ARRAY) y las cubren los stores de perfiles/usuarios.
PORTABLE_MIGRATION_MIN = "003"

# `:nombre` que no venga precedido de `:` (casts ::) ni de un carácter de
# palabra (horas '10:00' o texto pegado).
_PARAM_RE = re.compile(r"(?<![:\w]):([a-zA-Z_]\w*)")


def portable_migrations() -> list[Path]:
    return sorted(p for p in SQL_DIR.glob("*.sql") if p.name[:3] >= PORTABLE_MIGRATION_MIN)


def normalize_value(value: Any) -> Any:
    """Uniformiza lo que regresa cada driver: Decimal para números, ISO para
    fechas, bool para booleanos. Así el dominio no sabe qué motor hay abajo."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class Database(ABC):
    dialect: str = "generic"

    @abstractmethod
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[tuple]:
        """Ejecuta una sentencia y regresa las filas (vacío si no es SELECT)."""

    @abstractmethod
    def execute_many(self, sql: str, rows: list[dict[str, Any]]) -> None:
        """La misma sentencia para muchas filas (inserciones masivas)."""

    @abstractmethod
    def executescript(self, sql: str) -> None:
        """Varias sentencias separadas por ';' (migraciones)."""

    @abstractmethod
    def transaction(self) -> Iterator[None]:
        """Context manager: lo ejecutado adentro se confirma junto o se revierte junto."""

    @abstractmethod
    def ensure_schema(self) -> None:
        """Aplica las migraciones portables que falten (idempotente)."""

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def _rows_as_dicts(self, sql: str, params: dict[str, Any] | None) -> list[dict[str, Any]]: ...

    # ------------------------------------------------------------ helpers --

    def fetchone(self, sql: str, params: dict[str, Any] | None = None) -> tuple | None:
        rows = self.execute(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        row = self.fetchone(sql, params)
        return normalize_value(row[0]) if row else None

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Filas como dicts, con las columnas en minúsculas (Snowflake las
        regresa en MAYÚSCULAS, sqlite tal como se escribieron)."""
        return self._rows_as_dicts(sql, params)

    def row(self, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        rows = self._rows_as_dicts(sql, params)
        return rows[0] if rows else None
