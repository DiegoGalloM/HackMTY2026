from __future__ import annotations

import logging
import queue
import re
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import snowflake.connector

from app.config import Settings
from app.db.base import _PARAM_RE, Database, normalize_value

log = logging.getLogger(__name__)

POOL_SIZE = 4

# `INSERT INTO tabla (cols) VALUES (:a, :b, ...)` -> (cabecera, tupla de valores)
_INSERT_RE = re.compile(r"^(INSERT\s+INTO\s+\w+\s*\([^)]*\))\s*VALUES\s*(\([^)]*\))\s*$", re.IGNORECASE | re.DOTALL)


class SnowflakeDatabase(Database):
    """Pool pequeño de conexiones persistentes (abrir una cuesta ~1 s; cada
    consulta ~0.3 s de ida y vuelta). Varias pantallas pueden consultar en
    paralelo, y una transacción se queda con SU conexión (thread-local) desde
    BEGIN hasta COMMIT/ROLLBACK. autocommit encendido: cada sentencia suelta
    confirma sola sin un viaje extra."""

    dialect = "snowflake"

    def __init__(self, settings: Settings):
        self._settings = settings
        self._pool: queue.LifoQueue = queue.LifoQueue()
        self._created = 0
        self._create_lock = threading.Lock()
        self._local = threading.local()
        self.instance_id = uuid.uuid4().hex

    # --------------------------------------------------------- conexión --

    def _connect(self):
        s = self._settings
        return snowflake.connector.connect(
            account=s.snowflake_account,
            user=s.snowflake_user,
            password=s.snowflake_password,
            warehouse=s.snowflake_warehouse,
            database=s.snowflake_database,
            schema=s.snowflake_schema,
            role=s.snowflake_role or None,
            autocommit=True,
            client_session_keep_alive=True,
        )

    def _acquire(self):
        """(conexión, hay_que_devolverla). Dentro de una transacción se usa la
        conexión fijada al hilo y no se devuelve hasta que termine."""
        pinned = getattr(self._local, "tx_conn", None)
        if pinned is not None:
            return pinned, False
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            conn = None
            with self._create_lock:
                if self._created < POOL_SIZE:
                    self._created += 1
                    conn = self._connect()
            if conn is None:
                conn = self._pool.get(timeout=120)
        if conn.is_closed():
            conn = self._connect()
        return conn, True

    def _release(self, conn) -> None:
        self._pool.put(conn)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """Presta una conexión del pool a código que habla el dialecto del
        connector directamente (los stores de perfiles/usuarios)."""
        conn, release = self._acquire()
        try:
            yield conn
        finally:
            if release:
                self._release(conn)

    @staticmethod
    def _translate(sql: str) -> str:
        # `:nombre` -> `%(nombre)s`. El SQL del dominio no lleva '%' sueltos.
        return _PARAM_RE.sub(r"%(\1)s", sql)

    @staticmethod
    def _bind(params: dict[str, Any] | None) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in (params or {}).items():
            out[k] = str(v) if isinstance(v, Decimal) else v
        return out

    def _run(self, sql: str, params: dict[str, Any] | None, *, many: list[dict[str, Any]] | None = None):
        translated = self._translate(sql)
        conn, release = self._acquire()
        try:
            try:
                cur = conn.cursor()
                if many is not None:
                    cur.executemany(translated, [self._bind(r) for r in many])
                else:
                    cur.execute(translated, self._bind(params))
                return cur
            except (snowflake.connector.errors.OperationalError, snowflake.connector.errors.DatabaseError) as exc:
                # Sesión expirada o conexión caída: se reintenta una vez con una
                # conexión nueva, salvo dentro de una transacción (ahí reintentar
                # a medias sería peor que fallar).
                if not release or not _is_connection_error(exc):
                    raise
                log.warning("Snowflake: reconectando tras error de conexión: %s", exc)
                conn = self._connect()
                cur = conn.cursor()
                if many is not None:
                    cur.executemany(translated, [self._bind(r) for r in many])
                else:
                    cur.execute(translated, self._bind(params))
                return cur
        finally:
            if release:
                self._release(conn)

    # ------------------------------------------------------------- API --

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> list[tuple]:
        cur = self._run(sql, params)
        return cur.fetchall() if cur.description else []

    def _rows_as_dicts(self, sql: str, params: dict[str, Any] | None) -> list[dict[str, Any]]:
        cur = self._run(sql, params)
        cols = [c[0].lower() for c in cur.description or []]
        return [dict(zip(cols, (normalize_value(v) for v in row), strict=False)) for row in cur.fetchall()]

    def execute_many(self, sql: str, rows: list[dict[str, Any]], chunk: int = 200) -> None:
        """Inserción masiva. Un `INSERT INTO t (cols) VALUES (:a, :b)` se
        reescribe como UNA sentencia multi-fila por lote (200 filas ≈ 2 600
        binds), así 7 000 filas son ~35 viajes y no 7 000. Cualquier otra
        sentencia se ejecuta fila por fila."""
        if not rows:
            return
        match = _INSERT_RE.match(sql.strip())
        if not match:
            for row in rows:
                self._run(sql, row)
            return
        head, values_tpl = match.group(1), match.group(2)
        names = _PARAM_RE.findall(values_tpl)
        for i in range(0, len(rows), chunk):
            batch = rows[i : i + chunk]
            tuples, params = [], {}
            for j, row in enumerate(batch):
                cols = []
                for name in names:
                    key = f"{name}_{j}"
                    params[key] = row.get(name)
                    cols.append(f":{key}")
                tuples.append(f"({', '.join(cols)})")
            self._run(f"{head} VALUES {', '.join(tuples)}", params)

    def executescript(self, sql: str) -> None:
        conn, release = self._acquire()
        try:
            conn.execute_string(sql)
        finally:
            if release:
                self._release(conn)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        pinned = getattr(self._local, "tx_conn", None)
        if pinned is not None:  # anidada: la exterior confirma
            yield
            return
        conn, _ = self._acquire()
        self._local.tx_conn = conn
        try:
            conn.cursor().execute("BEGIN")
            yield
            conn.cursor().execute("COMMIT")
        except BaseException:
            try:
                conn.cursor().execute("ROLLBACK")
            except Exception:  # noqa: BLE001 - pragma: no cover - la conexión ya murió
                conn = None
            raise
        finally:
            self._local.tx_conn = None
            if conn is not None:
                self._release(conn)

    def ensure_schema(self) -> None:
        # Se reutiliza el runner de scripts/migrate.py: misma tabla
        # schema_migrations, mismo orden, mismo criterio de "ya aplicada".
        from scripts.migrate import apply_pending

        conn, release = self._acquire()
        try:
            apply_pending(conn, log_fn=lambda m: log.info("migraciones: %s", m))
        finally:
            if release:
                self._release(conn)

    def close(self) -> None:
        while True:
            try:
                self._pool.get_nowait().close()
            except queue.Empty:
                break


def _is_connection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return bool(re.search(r"session|expired|connection|closed|token|network|timeout", text))
