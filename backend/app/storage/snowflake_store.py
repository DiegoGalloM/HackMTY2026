import asyncio
import json
from typing import Any

import snowflake.connector

from app.config import Settings
from app.models.schemas import BusinessProfile
from app.storage.base import ProfileStore

# Deben coincidir con UNIVERSAL_QUESTIONS en frontend/src/onboarding/questions.js
UNIVERSAL_QUESTION_KEYS = [
    "vende_producto_fisico", "guarda_inventario", "compra_mayoreo",
    "se_ha_quedado_sin_stock", "compro_de_mas", "vende_en_local_fijo",
]


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
                    category = %(category)s, operating_days = PARSE_JSON(%(operating_days)s),
                    city = %(city)s, employees = %(employees)s, answers = PARSE_JSON(%(answers)s)
                WHEN NOT MATCHED THEN INSERT (owner_id, category, operating_days, city, employees, answers)
                VALUES (%(owner_id)s, %(category)s, PARSE_JSON(%(operating_days)s),
                        %(city)s, %(employees)s, PARSE_JSON(%(answers)s))
                """,
                {
                    "owner_id": owner_id, "category": profile.category,
                    "operating_days": json.dumps(profile.operating_days),
                    "city": profile.city, "employees": profile.employees,
                    "answers": json.dumps(profile.answers),
                },
            )
        finally:
            conn.close()

    async def save_profile(self, owner_id: str, profile: BusinessProfile) -> None:
        await asyncio.to_thread(self._save_profile_sync, owner_id, profile)

    def _row_to_profile(self, row) -> BusinessProfile:
        category, operating_days, city, employees, answers = row
        return BusinessProfile(
            category=category,
            operating_days=json.loads(operating_days) if isinstance(operating_days, str) else operating_days,
            city=city, employees=employees,
            answers=json.loads(answers) if isinstance(answers, str) else answers,
        )

    def _get_profile_sync(self, owner_id: str) -> BusinessProfile | None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT category, operating_days, city, employees, answers FROM business_profiles WHERE owner_id = %(owner_id)s",
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
                    "SELECT category, operating_days, city, employees, answers FROM business_profiles WHERE category = %(category)s",
                    {"category": category},
                )
            else:
                cur.execute("SELECT category, operating_days, city, employees, answers FROM business_profiles")
            return [self._row_to_profile(row) for row in cur.fetchall()]
        finally:
            conn.close()

    async def list_profiles(self, category: str | None = None) -> list[BusinessProfile]:
        return await asyncio.to_thread(self._list_profiles_sync, category)

    def _category_stats_sync(self, category: str) -> dict[str, Any]:
        pct_columns = ",\n            ".join(
            f'AVG(IFF(answers:{key}::boolean, 1, 0)) AS "{key}"' for key in UNIVERSAL_QUESTION_KEYS
        )
        sql = f"""
            SELECT COUNT(*) AS n_negocios,
            {pct_columns}
            FROM business_profiles
            WHERE category = %(category)s
        """
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, {"category": category})
            row = cur.fetchone()
            columns = [c[0] for c in cur.description]
        finally:
            conn.close()

        if not row or row[0] == 0:
            return {"category": category, "n_negocios": 0, "answers_pct_true": {}}

        data = dict(zip(columns, row))
        n = data.pop("N_NEGOCIOS", data.pop("n_negocios", 0))
        return {
            "category": category, "n_negocios": n,
            "answers_pct_true": {k: round(float(v), 2) for k, v in data.items() if v is not None},
        }

    async def category_stats(self, category: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._category_stats_sync, category)