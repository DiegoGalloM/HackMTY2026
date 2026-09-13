"""
Capa de acceso a datos del núcleo financiero.

Una sola interfaz (`Database`) con dos implementaciones intercambiables por
variable de entorno, igual que los stores de perfiles:

  - SqliteDatabase     USE_SNOWFLAKE=false — en memoria (o archivo con LOCAL_DB_PATH).
                       Sirve para desarrollar, para los tests y para la demo sin red.
  - SnowflakeDatabase  USE_SNOWFLAKE=true  — conexión persistente a Snowflake.

El SQL del dominio se escribe UNA vez en un subconjunto portable (ver
docs/FINANCIAL_CORE.md) y corre igual en los dos motores.
"""

from functools import lru_cache

from app.config import get_settings
from app.db.base import Database


@lru_cache
def get_db() -> Database:
    settings = get_settings()
    if settings.use_snowflake and settings.snowflake_account:
        from app.db.snowflake_db import SnowflakeDatabase

        db: Database = SnowflakeDatabase(settings)
    else:
        from app.db.sqlite_db import SqliteDatabase

        db = SqliteDatabase(settings.local_db_path or ":memory:")
    db.ensure_schema()
    return db
