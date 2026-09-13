import json
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DB = os.environ["SNOWFLAKE_DATABASE"]
OUT_DIR = ROOT / "snowflake-out"
OUT_DIR.mkdir(exist_ok=True)


def write_json(filename, data):
    with open(OUT_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def query(cursor, sql, params=None):
    cursor.execute(sql, params)

    columns = [c[0] for c in cursor.description]

    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=DB,
    schema=os.environ.get("SNOWFLAKE_SCHEMA") or None,
    role=os.environ.get("SNOWFLAKE_ROLE") or None,
)

try:
    cursor = conn.cursor()

    # -------------------------
    # DDL
    # -------------------------

    cursor.execute("SELECT GET_DDL('DATABASE', %s, TRUE)", (DB,))

    ddl = cursor.fetchone()[0]

    with open(OUT_DIR / "schema.sql", "w", encoding="utf-8") as f:
        f.write(ddl)

    # -------------------------
    # TABLES
    # -------------------------

    tables = query(cursor, """
    SELECT
        TABLE_SCHEMA,
        TABLE_NAME,
        TABLE_TYPE,
        ROW_COUNT,
        BYTES,
        COMMENT
    FROM IDENTIFIER(%s)
    WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """, (f"{DB}.INFORMATION_SCHEMA.TABLES",))

    write_json("tables.json", tables)

    # -------------------------
    # COLUMNS
    # -------------------------

    columns = query(cursor, """
    SELECT
        TABLE_SCHEMA,
        TABLE_NAME,
        COLUMN_NAME,
        ORDINAL_POSITION,
        DATA_TYPE,
        IS_NULLABLE,
        COLUMN_DEFAULT,
        COMMENT
    FROM IDENTIFIER(%s)
    WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA'
    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
    """, (f"{DB}.INFORMATION_SCHEMA.COLUMNS",))

    write_json("columns.json", columns)

    # -------------------------
    # CONSTRAINTS
    # -------------------------

    constraints = query(cursor, """
    SELECT
        CONSTRAINT_SCHEMA,
        CONSTRAINT_NAME,
        TABLE_SCHEMA,
        TABLE_NAME,
        CONSTRAINT_TYPE
    FROM IDENTIFIER(%s)
    WHERE TABLE_SCHEMA <> 'INFORMATION_SCHEMA'
    ORDER BY TABLE_SCHEMA, TABLE_NAME, CONSTRAINT_NAME
    """, (f"{DB}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS",))

    write_json("relationships.json", constraints)

    print(
        f"{DB}: {len(tables)} tables, {len(columns)} columns, "
        f"{len(constraints)} constraints"
    )
finally:
    conn.close()
