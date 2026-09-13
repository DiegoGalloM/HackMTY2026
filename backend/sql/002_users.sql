-- 002_users.sql
-- Usuarios del registro/login. Las columnas corresponden 1:1 con StoredUser
-- (backend/app/models/schemas.py); el test tests/test_auth.py verifica que no se
-- desincronicen.
--
-- IMPORTANTE: Snowflake ACEPTA la sintaxis PRIMARY KEY / UNIQUE pero NO la
-- impone — son metadata para herramientas de modelado, nada más. Se puede
-- insertar dos veces el mismo username sin que la base se queje. Por eso:
--   1) aquí no se declara UNIQUE, para que nadie asuma que hay protección, y
--   2) la unicidad la garantiza SnowflakeUserStore._create_user_sync con un
--      INSERT ... SELECT ... WHERE NOT EXISTS y revisando rowcount.
-- Si algún día se migra a Postgres, ahí SÍ conviene agregar UNIQUE(username).

CREATE TABLE IF NOT EXISTS users (
  user_id STRING,
  username STRING NOT NULL,
  business_name STRING NOT NULL,
  full_name STRING NOT NULL,
  birthdate DATE NOT NULL,
  password_hash STRING NOT NULL,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
