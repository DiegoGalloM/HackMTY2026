"""
Limpia el audio de la encuesta que quedó guardado DENTRO de business_profiles
antes de la Fase 5 (columnas week_description_audio_base64 / _mime).

Desde la Fase 5 el audio vive en onboarding_audio con caducidad y el backend ya
no lo lee de la fila, pero las filas viejas lo siguen teniendo. Borrarlo es
destructivo, así que NO va en backend/sql/ (esas migraciones se aplican solas
al arrancar con USE_SNOWFLAKE=true): es un paso manual de la Fase 9.

Se usa desde `backend/`:

    python -m scripts.purge_legacy_profile_audio          # sólo cuenta (simulación)
    python -m scripts.purge_legacy_profile_audio --apply  # vacía las columnas

No borra perfiles ni columnas: sólo pone en NULL el audio y su MIME.
"""

import argparse
import sys

from app.config import get_settings

COUNT_SQL = "SELECT COUNT(*) FROM business_profiles WHERE week_description_audio_base64 IS NOT NULL"
PURGE_SQL = (
    "UPDATE business_profiles SET week_description_audio_base64 = NULL, week_description_audio_mime = NULL "
    "WHERE week_description_audio_base64 IS NOT NULL"
)


def purge(conn, apply: bool, log_fn=print) -> int:
    """Regresa cuántas filas tenían audio. Con apply=False no modifica nada."""
    cur = conn.cursor()
    cur.execute(COUNT_SQL)
    pending = int(cur.fetchone()[0] or 0)
    if pending == 0:
        log_fn("No hay audio guardado en business_profiles. Nada que limpiar.")
        return 0
    if not apply:
        log_fn(f"{pending} perfil(es) tienen audio en la fila. Simulación: no se modificó nada.")
        log_fn("Para vaciarlo: python -m scripts.purge_legacy_profile_audio --apply")
        return pending
    cur.execute(PURGE_SQL)
    log_fn(f"Listo: se vació el audio de {pending} perfil(es).")
    return pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="vacía las columnas (sin esto sólo cuenta)")
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.use_snowflake or not settings.snowflake_account:
        # Igual que scripts/migrate.py: sin Snowflake no hay filas viejas que
        # limpiar (los perfiles en memoria ya se guardan sin audio).
        print("Snowflake está apagado (USE_SNOWFLAKE=false o SNOWFLAKE_ACCOUNT vacío). Nada que limpiar.")
        return 0

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
        purge(conn, apply=args.apply)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
