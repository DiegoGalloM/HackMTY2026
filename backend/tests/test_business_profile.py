"""
Tests de la capa de perfiles de negocio (encuesta de onboarding).

Los dos primeros corren contra MemoryProfileStore vía la API real. El tercero
revisa el SQL de SnowflakeProfileStore **sin conectarse a Snowflake**: compara
las columnas que el store escribe contra los campos de BusinessProfile. Así, si
alguien agrega un campo al schema y se le olvida la columna, truena aquí en vez
de perderse en silencio en producción.
"""

import inspect
import re

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import BusinessProfile
from app.routers.business_profile import MIN_COHORT
from app.storage import snowflake_store
from tests.conftest import auth_headers, seed_user

client = TestClient(app)

# Los endpoints /business-profile/{owner_id} ahora exigen Bearer token del dueño,
# así que cada test registra su usuario con user_id = el owner_id que usa. Los ids
# siguen siendo fijos (no uuid) porque con USE_SNOWFLAKE=true estos tests escriben
# en la tabla real: un id nuevo por corrida haría crecer n_negocios cada vez.
OWNER_ROUNDTRIP = "test_roundtrip"
OWNER_STATS = "test_stats_1"

# Ojo: la categoría es de prueba a propósito. Con USE_SNOWFLAKE=true estos tests
# escriben en la tabla real, así que no deben ensuciar las stats de una categoría
# de verdad ("comida", "retail", ...) que se use en la demo.
FULL_PROFILE = {
    "category": "test_categoria",
    "category_detail": "taquería",
    "operating_days": ["mon", "tue", "wed"],
    "city": "Monterrey",
    "employees": "1",
    "answers": {"se_ha_quedado_sin_stock": True, "compro_de_mas": False},
    "week_description_mode": "audio",
    "week_description_text": None,
    "week_description_audio_base64": "UklGRhoAAABXQVZF",
    "week_description_audio_mime": "audio/webm",
}


def test_save_and_get_profile_preserves_every_field():
    """El GET tiene que regresar todo lo que mandó el POST — incluida la
    grabación de voz de la semana, que es la que más fácil se pierde."""
    seed_user(OWNER_ROUNDTRIP, "owner_roundtrip")
    headers = auth_headers(OWNER_ROUNDTRIP)

    assert client.post(
        f"/business-profile/{OWNER_ROUNDTRIP}", json=FULL_PROFILE, headers=headers
    ).status_code == 200

    saved = client.get(f"/business-profile/{OWNER_ROUNDTRIP}", headers=headers).json()
    for field, expected in FULL_PROFILE.items():
        assert saved[field] == expected, f"campo '{field}' no sobrevivió el round-trip"


def test_category_stats_includes_always_false_questions():
    """answers_pct_true reporta todas las preguntas de la categoría, no solo las
    que salieron True. Las dos implementaciones de store tienen que coincidir en
    esta forma, porque el endpoint no sabe cuál está activa."""
    # Se siembran MIN_COHORT negocios: por debajo de ese umbral el endpoint
    # público oculta el desglose (ver test_category_stats_hides_small_cohorts).
    for i in range(MIN_COHORT):
        owner = f"{OWNER_STATS}_{i}"
        seed_user(owner, f"owner_stats_{i}")
        client.post(
            f"/business-profile/{owner}",
            json={**FULL_PROFILE, "category": "stats_test"},
            headers=auth_headers(owner),
        )

    # stats sigue siendo público: se consulta sin token a propósito.
    stats = client.get("/business-profile/stats/stats_test").json()
    assert stats["n_negocios"] == MIN_COHORT
    assert stats["answers_pct_true"]["se_ha_quedado_sin_stock"] == 1.0
    assert stats["answers_pct_true"]["compro_de_mas"] == 0.0


def test_category_stats_hides_small_cohorts():
    """Con pocos negocios en la categoría, cada porcentaje ES la respuesta
    literal de uno de ellos. Como la categoría la escribe el usuario, cualquiera
    podría inventar una categoría rara, quedarse solo en ella y leer sus
    respuestas sin token. Debajo del umbral se publica el conteo, no el desglose.
    """
    owner = "test_stats_solo"
    seed_user(owner, "owner_stats_solo")
    client.post(
        f"/business-profile/{owner}",
        json={**FULL_PROFILE, "category": "categoria_de_uno"},
        headers=auth_headers(owner),
    )

    stats = client.get("/business-profile/stats/categoria_de_uno").json()
    assert stats["n_negocios"] == 1
    assert stats["answers_pct_true"] == {}
    assert stats["below_min_cohort"] is True


def test_snowflake_store_covers_all_profile_fields():
    """Guard de esquema: el SELECT y el MERGE de SnowflakeProfileStore tienen que
    mencionar cada campo de BusinessProfile. No abre conexión a Snowflake."""
    expected = set(BusinessProfile.model_fields)

    selected = {c.strip() for c in snowflake_store.PROFILE_COLUMNS.split(",")}
    assert selected == expected, f"columnas faltantes en el SELECT: {expected - selected}"

    merge_sql = inspect.getsource(snowflake_store.SnowflakeProfileStore._save_profile_sync)
    written = set(re.findall(r"%\((\w+)\)s", merge_sql))
    assert expected <= written, f"campos que el MERGE nunca escribe: {expected - written}"
