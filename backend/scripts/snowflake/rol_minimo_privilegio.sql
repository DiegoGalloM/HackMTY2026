-- backend/scripts/snowflake/rol_minimo_privilegio.sql
--
-- Rol y usuario de servicio con el mínimo privilegio para el backend
-- desplegado. Hoy render.yaml conecta con SNOWFLAKE_ROLE=ACCOUNTADMIN: si esa
-- contraseña se filtra, quien la tenga administra la cuenta entera (usuarios,
-- facturación, otras bases). Con este rol sólo puede leer y escribir las
-- tablas de la app en HACKMTY.PUBLIC.
--
-- NO vive en backend/sql/ a propósito: el runner de migraciones aplica todo lo
-- que hay ahí al arrancar, y crear roles y usuarios no es trabajo del backend
-- (tests/test_snowflake_role_script.py lo vigila). Se corre UNA vez, a mano,
-- en un worksheet de Snowsight con una persona administradora. Es la Fase 9 de
-- docs/ROADMAP_PULIDO.md; el paso a paso está en docs/SNOWFLAKE_SETUP.md
-- ("Rol de mínimo privilegio").
--
-- Antes de correrlo:
--   1. Las migraciones ya deben estar aplicadas (python -m scripts.migrate con
--      el usuario administrador): 001 crea el warehouse, la base y el schema, y
--      eso sí requiere privilegios de cuenta.
--   2. Cambien <CONTRASEÑA_LARGA_Y_ALEATORIA> por una generada, p. ej.:
--      python -c "import secrets; print(secrets.token_urlsafe(32))"
--      y guárdenla sólo en Render (SNOWFLAKE_PASSWORD). No la commiteen.
--
-- Todo es IF NOT EXISTS / GRANT idempotente: correrlo dos veces no hace daño.

-- 1) Rol y usuario (SECURITYADMIN administra roles, usuarios y grants) ---------
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS HACKMTY_APP
  COMMENT = 'Backend de Capital One Business (HackMTY 2026): solo datos de HACKMTY.PUBLIC';

-- La jerarquía recomendada: SYSADMIN hereda el rol y puede administrar lo que cree.
GRANT ROLE HACKMTY_APP TO ROLE SYSADMIN;

-- TYPE = LEGACY_SERVICE: usuario de servicio (sin MFA ni login a Snowsight)
-- que todavía acepta contraseña, que es como conecta hoy app/db/snowflake_db.py.
-- Snowflake está retirando la contraseña sola: revisen la política vigente de
-- su cuenta en la Fase 9; el camino de largo plazo es TYPE = SERVICE con par de
-- llaves (RSA_PUBLIC_KEY), que requiere soportar private_key en el conector.
CREATE USER IF NOT EXISTS HACKMTY_APP_SVC
  TYPE = LEGACY_SERVICE
  PASSWORD = '<CONTRASEÑA_LARGA_Y_ALEATORIA>'
  DEFAULT_ROLE = HACKMTY_APP
  DEFAULT_WAREHOUSE = HACKMTY_WH
  DEFAULT_NAMESPACE = HACKMTY.PUBLIC
  COMMENT = 'Usuario del backend en Render';

GRANT ROLE HACKMTY_APP TO USER HACKMTY_APP_SVC;

-- 2) Cómputo: sólo usar el warehouse (AUTO_RESUME lo despierta), no cambiarlo --
GRANT USAGE ON WAREHOUSE HACKMTY_WH TO ROLE HACKMTY_APP;

-- 3) Llegar al schema ---------------------------------------------------------
GRANT USAGE ON DATABASE HACKMTY TO ROLE HACKMTY_APP;
GRANT USAGE ON SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;

-- 4) Datos: lo que hace el backend (SELECT, INSERT, UPDATE, DELETE y MERGE) ---
-- MERGE no es un privilegio aparte: usa INSERT + UPDATE (+ DELETE si aplica).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;
GRANT SELECT ON ALL VIEWS IN SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;
-- Lo que creen migraciones futuras hereda los mismos permisos.
GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;

-- 5) Migraciones al arrancar --------------------------------------------------
-- El backend corre apply_pending() en cada arranque. Con estos dos grants un
-- deploy puede crear tablas y vistas nuevas en ESTE schema (nada fuera de él).
-- Una migración con ALTER TABLE sobre una tabla creada por ACCOUNTADMIN
-- fallaría (ALTER exige ser dueño): esas se corren a mano con el administrador,
-- o se omiten estos dos grants y TODAS las migraciones se corren a mano.
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA HACKMTY.PUBLIC TO ROLE HACKMTY_APP;

-- 6) Asistente: SNOWFLAKE.CORTEX.COMPLETE (app/finance/llm.py) ----------------
-- Viene con PUBLIC por default, pero si la cuenta se lo quitó a PUBLIC el
-- asistente cae a plantillas en silencio. Explícito es mejor.
USE ROLE ACCOUNTADMIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE HACKMTY_APP;

-- 7) Verificación ---------------------------------------------------------------
SHOW GRANTS TO ROLE HACKMTY_APP;

USE ROLE HACKMTY_APP;
USE WAREHOUSE HACKMTY_WH;
SELECT COUNT(*) AS users FROM HACKMTY.PUBLIC.users;
SELECT COUNT(*) AS migraciones FROM HACKMTY.PUBLIC.schema_migrations;
-- Esto DEBE fallar con "Insufficient privileges": el rol no administra la cuenta.
-- CREATE DATABASE HACKMTY_PRUEBA_NO_DEBE_EXISTIR;

-- Después, en Render: SNOWFLAKE_USER=HACKMTY_APP_SVC, SNOWFLAKE_PASSWORD=<la de
-- arriba>, SNOWFLAKE_ROLE=HACKMTY_APP; redeploy y GET /health/ready debe dar
-- checks.database.status = "ok" (y checks.llm "ok" con Cortex). Recién
-- entonces cambien SNOWFLAKE_ROLE en render.yaml y quiten ACCOUNTADMIN.
