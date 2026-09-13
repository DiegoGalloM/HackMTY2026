from __future__ import annotations

import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.db.base import Database, normalize_value, portable_migrations

_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename VARCHAR,
  applied_at VARCHAR
)
"""


class SqliteDatabase(Database):
    """sqlite con una sola conexión compartida y un RLock: el backend llama a
    la base desde hilos (asyncio.to_thread), y una transacción tiene que ver
    sus propias escrituras hasta que confirme."""

    dialect = "sqlite"

    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.RLock()
        self._in_tx = 0
        # Identidad estable para las cachés: id() se recicla entre objetos.
        self.instance_id = uuid.uuid4().hex

    @staticmethod
    def _bind(params: dict[str, Any] | None) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in (params or {}).items():
            if isinstance(v, Decimal):
                out[k] = float(v)
            elif isinstance(v, bool):
                out[k] = 1 if v else 0
            else:
                out[k] = v
        return out

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[tuple]:
        with self._lock:
            cur = self._conn.execute(sql, self._bind(params))
            if cur.description is None:
                return []
            return cur.fetchall()

    def _rows_as_dicts(self, sql: str, params: dict[str, Any] | None) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(sql, self._bind(params))
            cols = [c[0].lower() for c in cur.description or []]
            return [dict(zip(cols, (normalize_value(v) for v in row), strict=False)) for row in cur.fetchall()]

    def execute_many(self, sql: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with self._lock:
            self._conn.executemany(sql, [self._bind(r) for r in rows])

    def executescript(self, sql: str) -> None:
        with self._lock:
            self._conn.executescript(sql)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            outer = self._in_tx == 0
            if outer:
                self._conn.execute("BEGIN")
            self._in_tx += 1
            try:
                yield
                if outer:
                    self._conn.execute("COMMIT")
            except BaseException:
                if outer:
                    self._conn.execute("ROLLBACK")
                raise
            finally:
                self._in_tx -= 1

    def ensure_schema(self) -> None:
        with self._lock:
            self._conn.execute(_MIGRATIONS_TABLE)
            applied = {r[0] for r in self._conn.execute("SELECT filename FROM schema_migrations")}
            for path in portable_migrations():
                if path.name in applied:
                    continue
                self._conn.executescript(path.read_text(encoding="utf-8"))
                self._conn.execute(
                    "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, datetime('now'))",
                    (path.name,),
                )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
