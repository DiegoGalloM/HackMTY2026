import asyncio
import json
from typing import Any

import snowflake.connector

from app.config import Settings
from app.models.schemas import BusinessProfile
from app.storage.base import ProfileStore

# Columnas que se leen para reconstruir un BusinessProfile completo.
# El orden tiene que coincidir con _row_to_profile().
PROFILE_COLUMNS = """
    category, category_detail, operating_days, city, employees, answers,
    week_description_mode, week_description_text,
    week_description_audio_base64, week_description_audio_mime
"""


class SnowflakeProfileStore(ProfileStore):
    def __init__(self, settings: Settings):
        self._settings = settings

    def _connect(self):
        return snowflake.connector.connect(
            account=self._settings.snowflake_account,
            user=self._settings.snowflake_user,
            password=self._settings.snowflake_password,
            warehouse=self._settings.snowflake_warehouse,
            database=self._settings.snowflake_database,
            schema=self._settings.snowflake_schema,
            role=self._settings.snowflake_role or None,
        )

    def _save_profile_sync(self, owner_id: str, profile: BusinessProfile) -> None:
        conn = self._connect()
        try:
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
                    week_description_audio_base64 = %(week_description_audio_base64)s,
                    week_description_audio_mime = %(week_description_audio_mime)s
                WHEN NOT MATCHED THEN INSERT (
                    owner_id, category, category_detail, operating_days, city, employees, answers,
                    week_description_mode, week_description_text,
                    week_description_audio_base64, week_description_audio_mime)
                VALUES (%(owner_id)s, %(category)s, %(category_detail)s, PARSE_JSON(%(operating_days)s),
                        %(city)s, %(employees)s, PARSE_JSON(%(answers)s),
                        %(week_description_mode)s, %(week_description_text)s,
                        %(week_description_audio_base64)s, %(week_description_audio_mime)s)
                """,
                {
                    "owner_id": owner_id, "category": profile.category,
                    "category_detail": profile.category_detail,
                    "operating_days": json.dumps(profile.operating_days),
                    "city": profile.city, "employees": profile.employees,
                    "answers": json.dumps(profile.answers),
                    "week_description_mode": profile.week_description_mode,
                    "week_description_text": profile.week_description_text,
                    "week_description_audio_base64": profile.week_description_audio_base64,
                    "week_description_audio_mime": profile.week_description_audio_mime,
                },
            )
        finally:
            conn.close()

    async def save_profile(self, owner_id: str, profile: BusinessProfile) -> None:
        await asyncio.to_thread(self._save_profile_sync, owner_id, profile)

    def _row_to_profile(self, row) -> BusinessProfile:
        (category, category_detail, operating_days, city, employees, answers,
         week_mode, week_text, week_audio_b64, week_audio_mime) = row
        return BusinessProfile(
            category=category,
            category_detail=category_detail,
            operating_days=json.loads(operating_days) if isinstance(operating_days, str) else operating_days,
            city=city, employees=employees,
            answers=json.loads(answers) if isinstance(answers, str) else answers,
            week_description_mode=week_mode,
            week_description_text=week_text,
            week_description_audio_base64=week_audio_b64,
            week_description_audio_mime=week_audio_mime,
        )

    def _get_profile_sync(self, owner_id: str) -> BusinessProfile | None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {PROFILE_COLUMNS} FROM business_profiles WHERE owner_id = %(owner_id)s",
                {"owner_id": owner_id},
            )
            row = cur.fetchone()
            return self._row_to_profile(row) if row else None
        finally:
            conn.close()

    async def get_profile(self, owner_id: str) -> BusinessProfile | None:
        return await asyncio.to_thread(self._get_profile_sync, owner_id)

    def _list_profiles_sync(self, category: str | None) -> list[BusinessProfile]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            if category:
                cur.execute(
                    f"SELECT {PROFILE_COLUMNS} FROM business_profiles WHERE category = %(category)s",
                    {"category": category},
                )
            else:
                cur.execute(f"SELECT {PROFILE_COLUMNS} FROM business_profiles")
            return [self._row_to_profile(row) for row in cur.fetchall()]
        finally:
            conn.close()

    async def list_profiles(self, category: str | None = None) -> list[BusinessProfile]:
        return await asyncio.to_thread(self._list_profiles_sync, category)

    def _category_stats_sync(self, category: str) -> dict[str, Any]:
        # FLATTEN sobre el VARIANT en vez de una lista fija de preguntas: así las
        # preguntas por categoría (ingredientes_perecederos, etc.) también cuentan,
        # igual que en MemoryProfileStore. Denominador = negocios de la categoría.
        conn = self._connect()
        try:
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
        finally:
            conn.close()

        return {
            "category": category,
            "n_negocios": n,
            "answers_pct_true": {question: round(int(n_true) / n, 2) for question, n_true in rows},
        }

    async def category_stats(self, category: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._category_stats_sync, category)
