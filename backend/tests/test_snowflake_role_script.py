"""El script del rol de mínimo privilegio (Fase 9) se revisa sin conectarse a
Snowflake: que no se cuele al runner de migraciones y que no le dé al backend
más de lo que usa."""

import re
from pathlib import Path

from scripts.migrate import SQL_DIR

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "snowflake" / "rol_minimo_privilegio.sql"


def _statements() -> list[str]:
    code = "\n".join(line for line in SCRIPT.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--"))
    return [" ".join(s.split()).upper() for s in code.split(";") if s.strip()]


def _grants_to_app_role() -> list[str]:
    return [s for s in _statements() if s.startswith("GRANT ") and s.endswith("TO ROLE HACKMTY_APP")]


def test_role_script_is_not_a_migration():
    # apply_pending() corre todo backend/sql/*.sql al arrancar: crear usuarios
    # y roles desde el backend exigiría justo los privilegios que se quieren quitar.
    assert SCRIPT.exists()
    assert SQL_DIR not in SCRIPT.parents
    assert not [p.name for p in SQL_DIR.glob("*.sql") if re.search(r"\b(CREATE (ROLE|USER)|GRANT )", p.read_text(encoding="utf-8"), re.IGNORECASE)]


def test_app_role_only_gets_data_access_on_its_schema():
    grants = _grants_to_app_role()
    assert grants
    for grant in grants:
        assert "ACCOUNTADMIN" not in grant and "SECURITYADMIN" not in grant, grant
        assert not re.search(r"\bGRANT (ALL|OWNERSHIP|MANAGE GRANTS)\b", grant), grant
        assert " ON ACCOUNT " not in grant, grant
        assert re.search(r" ON (WAREHOUSE HACKMTY_WH|DATABASE HACKMTY|SCHEMA HACKMTY\.PUBLIC|(ALL|FUTURE) (TABLES|VIEWS) IN SCHEMA HACKMTY\.PUBLIC) ", grant) or "SNOWFLAKE.CORTEX_USER" in grant, grant
    joined = "\n".join(grants)
    # Lo que el backend sí hace: MERGE/INSERT/UPDATE/DELETE, las vistas del
    # libro mayor, migraciones nuevas y SNOWFLAKE.CORTEX.COMPLETE.
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA HACKMTY.PUBLIC" in joined
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA HACKMTY.PUBLIC" in joined
    assert "GRANT SELECT ON ALL VIEWS IN SCHEMA HACKMTY.PUBLIC" in joined
    assert "GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER" in joined


def test_script_ships_no_real_password():
    users = [s for s in _statements() if s.startswith("CREATE USER")]
    assert len(users) == 1
    assert "PASSWORD = '<CONTRASEÑA_LARGA_Y_ALEATORIA>'" in users[0]
    assert "DEFAULT_ROLE = HACKMTY_APP" in users[0]
