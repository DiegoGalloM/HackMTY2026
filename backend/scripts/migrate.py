"""
Corredor de migraciones de Snowflake.

Se usa desde `backend/`:

    python -m scripts.migrate

Lee `backend/sql/*.sql` en orden alfabético (por eso van numerados), aplica los
que falten y anota cada uno en la tabla `schema_migrations`. Correrlo dos veces
seguidas es seguro: la segunda vez no hace nada.

`apply_pending()` es la misma lógica reutilizable: el backend la llama al
arrancar con USE_SNOWFLAKE=true, así un deploy nuevo se auto-migra.
"""

import sys
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"

MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename STRING,
  applied_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
"""


def apply_pending(conn, log_fn: Callable[[str], None] = print) -> int:
    """Aplica las migraciones que falten sobre una conexión abierta. Regresa
    cuántas aplicó."""
    files = sorted(SQL_DIR.glob("*.sql"))
    if not files:
        log_fn(f"No se encontraron archivos .sql en {SQL_DIR}")
        return 0

    cur = conn.cursor()
    cur.execute(MIGRATIONS_TABLE)
    cur.execute("SELECT filename FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    pending = [f for f in files if f.name not in applied]
    if not pending:
        log_fn(f"Todo al día: {len(files)} migración(es) ya aplicadas.")
        return 0

    for path in pending:
        log_fn(f"Aplicando {path.name}...")
        # execute_string y no execute: los archivos traen varias sentencias
        # separadas por ';' y execute() solo acepta una.
        conn.execute_string(path.read_text(encoding="utf-8"))
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%(filename)s)",
            {"filename": path.name},
        )
        log_fn(f"  OK {path.name}")

    log_fn(f"Listo: {len(pending)} migración(es) aplicadas.")
    return len(pending)


def main() -> int:
    settings = get_settings()

    if not settings.use_snowflake or not settings.snowflake_account:
        # Salir con 0 y no con error: correr las migraciones sin Snowflake
        # configurado es lo normal cuando alguien trabaja en memoria, no una falla.
        print(
            "Snowflake está apagado (USE_SNOWFLAKE=false o SNOWFLAKE_ACCOUNT vacío).\n"
            "No hay nada que migrar: el backend está usando los stores en memoria.\n"
            "Para activarlo, llena backend/.env siguiendo docs/SNOWFLAKE_SETUP.md."
        )
        return 0

    # El import va aquí adentro para que el mensaje de arriba funcione incluso si
    # el connector no está instalado todavía.
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
        role=settings.snowflake_role or None,
    )
    try:
        apply_pending(conn)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
