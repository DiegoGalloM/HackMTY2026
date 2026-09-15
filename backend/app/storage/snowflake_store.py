import asyncio
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import snowflake.connector

from app.config import Settings
from app.models.schemas import BusinessProfile, StoredUser
from app.storage.base import ProfileStore, UserStore

# Columnas que se leen para reconstruir un BusinessProfile completo.
# El orden tiene que coincidir con _row_to_profile().
PROFILE_COLUMNS = """
    category, category_detail, operating_days, city, employees, answers,
    week_description_mode, week_description_text
"""

# Campos de BusinessProfile que a propósito NO viven en business_profiles: el
# audio de la encuesta va a onboarding_audio, con caducidad (app/storage/
# audio_store.py). Las columnas siguen en la tabla sólo por compatibilidad con
# filas viejas; el MERGE las vacía y nunca se leen.
AUDIO_FIELDS_OUTSIDE_ROW = ("week_description_audio_base64", "week_description_audio_mime")

# Igual que PROFILE_COLUMNS: el orden tiene que coincidir con _row_to_user().
USER_COLUMNS = "user_id, username, business_name, full_name, birthdate, password_hash"


@contextmanager
def _connection(settings: Settings) -> Iterator[Any]:
    """Conexión a Snowflake. Si el núcleo financiero ya tiene su pool
    (USE_SNOWFLAKE=true), se toma prestada una de ahí: abrir una conexión
    nueva cuesta ~1 s y estos stores se consultan en cada request (token,
    perfil). Si no, se abre y se cierra una, como antes."""
    pooled = None
    try:
        from app.db import get_db

        candidate = get_db()
        if getattr(candidate, "dialect", "") == "snowflake":
            pooled = candidate
    except Exception:  # noqa: BLE001 - sin pool, conexión directa
        pooled = None
    if pooled is not None:
        with pooled.connection() as conn:
            yield conn
        return
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
        yield conn
    finally:
        conn.close()


class SnowflakeProfileStore(ProfileStore):
    def __init__(self, settings: Settings):
        self._settings = settings

    def _save_profile_sync(self, owner_id: str, profile: BusinessProfile) -> None:
        with _connection(self._settings) as conn:
            conn.cursor().execute(
                """
                MERGE INTO business_profiles AS target
                USING (SELECT %(owner_id)s AS owner_id) AS source
                ON target.owner_id = source.owner_id
                WHEN MATCHED THEN UPDATE SET
                    category = %(category)s, category_detail = %(category_detail)s,
                    operating_days = PARSE_JSON(%(operating_days)s),
                    city = %(city)s, employees = %(employees)s, answers = PARSE_JSON(%(answers)s),
                    week_description_mode = %(week_description_mode)s,
                    week_description_text = %(week_description_text)s,
                    week_description_audio_base64 = NULL,
                    week_description_audio_mime = NULL
                WHEN NOT MATCHED THEN INSERT (
                    owner_id, category, category_detail, operating_days, city, employees, answers,
                    week_description_mode, week_description_text)
                VALUES (%(owner_id)s, %(category)s, %(category_detail)s, PARSE_JSON(%(operating_days)s),
                        %(city)s, %(employees)s, PARSE_JSON(%(answers)s),
                        %(week_description_mode)s, %(week_description_text)s)
                """,
                {
                    "owner_id": owner_id, "category": profile.category,
                    "category_detail": profile.category_detail,
                    "operating_days": json.dumps(profile.operating_days),
                    "city": profile.city, "employees": profile.employees,
                    "answers": json.dumps(profile.answers),
                    "week_description_mode": profile.week_description_mode,
                    "week_description_text": profile.week_description_text,
                },
            )

    async def save_profile(self, owner_id: str, profile: BusinessProfile) -> None:
        await asyncio.to_thread(self._save_profile_sync, owner_id, profile)

    def _row_to_profile(self, row) -> BusinessProfile:
        (category, category_detail, operating_days, city, employees, answers,
         week_mode, week_text) = row
        return BusinessProfile(
            category=category,
            category_detail=category_detail,
            operating_days=json.loads(operating_days) if isinstance(operating_days, str) else operating_days,
            city=city, employees=employees,
            answers=json.loads(answers) if isinstance(answers, str) else answers,
            week_description_mode=week_mode,
            week_description_text=week_text,
        )

    def _get_profile_sync(self, owner_id: str) -> BusinessProfile | None:
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {PROFILE_COLUMNS} FROM business_profiles WHERE owner_id = %(owner_id)s",
                {"owner_id": owner_id},
            )
            row = cur.fetchone()
            return self._row_to_profile(row) if row else None

    async def get_profile(self, owner_id: str) -> BusinessProfile | None:
        return await asyncio.to_thread(self._get_profile_sync, owner_id)

    def _list_profiles_sync(self, category: str | None) -> list[BusinessProfile]:
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            if category:
                cur.execute(
                    f"SELECT {PROFILE_COLUMNS} FROM business_profiles WHERE category = %(category)s",
                    {"category": category},
                )
            else:
                cur.execute(f"SELECT {PROFILE_COLUMNS} FROM business_profiles")
            return [self._row_to_profile(row) for row in cur.fetchall()]

    async def list_profiles(self, category: str | None = None) -> list[BusinessProfile]:
        return await asyncio.to_thread(self._list_profiles_sync, category)

    def _category_stats_sync(self, category: str) -> dict[str, Any]:
        # FLATTEN sobre el VARIANT en vez de una lista fija de preguntas: así las
        # preguntas por categoría (ingredientes_perecederos, etc.) también cuentan,
        # igual que en MemoryProfileStore. Denominador = negocios de la categoría.
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM business_profiles WHERE category = %(category)s",
                {"category": category},
            )
            n = cur.fetchone()[0] or 0
            if n == 0:
                return {"category": category, "n_negocios": 0, "answers_pct_true": {}}

            cur.execute(
                """
                SELECT f.key AS question, SUM(IFF(f.value::boolean, 1, 0)) AS n_true
                FROM business_profiles AS p, LATERAL FLATTEN(input => p.answers) AS f
                WHERE p.category = %(category)s
                GROUP BY f.key
                """,
                {"category": category},
            )
            rows = cur.fetchall()

        return {
            "category": category,
            "n_negocios": n,
            "answers_pct_true": {question: round(int(n_true) / n, 2) for question, n_true in rows},
        }

    async def category_stats(self, category: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._category_stats_sync, category)


class SnowflakeUserStore(UserStore):
    def __init__(self, settings: Settings):
        self._settings = settings

    def _create_user_sync(self, user: StoredUser) -> bool:
        # OJO: en Snowflake PRIMARY KEY y UNIQUE son *solo metadata*, no se
        # imponen — puedes insertar dos filas con el mismo username sin que la
        # base se queje. La unicidad se hace con MERGE y no con
        # INSERT ... WHERE NOT EXISTS: INSERT no toma lock sobre la tabla
        # destino, así que dos registros simultáneos del mismo username evalúan
        # el NOT EXISTS cada uno contra su propio snapshot, los dos ven "no
        # existe" y los dos entran. MERGE sí serializa sobre el destino (es la
        # razón por la que el MERGE de los perfiles ya era seguro).
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                MERGE INTO users AS target
                USING (SELECT %(username)s AS username) AS source
                ON LOWER(target.username) = source.username
                WHEN NOT MATCHED THEN INSERT (
                    user_id, username, business_name, full_name, birthdate, password_hash)
                VALUES (%(user_id)s, %(username)s, %(business_name)s, %(full_name)s,
                        TO_DATE(%(birthdate)s), %(password_hash)s)
                """,
                {
                    "user_id": user.user_id,
                    "username": user.username.strip().lower(),
                    "business_name": user.business_name,
                    "full_name": user.full_name,
                    "birthdate": user.birthdate,
                    "password_hash": user.password_hash,
                },
            )
            # MERGE regresa una fila con el número de filas insertadas. Se lee de
            # ahí y no de rowcount porque para MERGE el driver no lo reporta de
            # forma consistente; si por lo que sea no viene la fila, se cae a
            # rowcount en vez de asumir que se insertó.
            row = cur.fetchone()
            inserted = int(row[0]) if row and row[0] is not None else (cur.rowcount or 0)
            return inserted > 0

    async def create_user(self, user: StoredUser) -> bool:
        return await asyncio.to_thread(self._create_user_sync, user)

    def _row_to_user(self, row) -> StoredUser:
        user_id, username, business_name, full_name, birthdate, password_hash = row
        return StoredUser(
            user_id=user_id,
            username=username,
            business_name=business_name,
            full_name=full_name,
            # La columna es DATE, así que el driver regresa datetime.date;
            # el contrato con el frontend es string YYYY-MM-DD.
            birthdate=birthdate.isoformat() if hasattr(birthdate, "isoformat") else str(birthdate),
            password_hash=password_hash,
        )

    def _get_user_by_username_sync(self, username: str) -> StoredUser | None:
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            cur.execute(
                # ORDER BY + LIMIT 1: si alguna vez llegaran a existir dos filas
                # con el mismo username (datos viejos, una carga manual), el
                # login debe resolver siempre contra la MISMA, la más antigua, y
                # no contra una cualquiera según el plan de ejecución.
                f"SELECT {USER_COLUMNS} FROM users WHERE LOWER(username) = %(username)s "
                "ORDER BY created_at LIMIT 1",
                {"username": username.strip().lower()},
            )
            row = cur.fetchone()
            return self._row_to_user(row) if row else None

    async def get_user_by_username(self, username: str) -> StoredUser | None:
        return await asyncio.to_thread(self._get_user_by_username_sync, username)

    def _get_user_by_id_sync(self, user_id: str) -> StoredUser | None:
        with _connection(self._settings) as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {USER_COLUMNS} FROM users WHERE user_id = %(user_id)s",
                {"user_id": user_id},
            )
            row = cur.fetchone()
            return self._row_to_user(row) if row else None

    async def get_user_by_id(self, user_id: str) -> StoredUser | None:
        return await asyncio.to_thread(self._get_user_by_id_sync, user_id)
