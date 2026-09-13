-- 001_business_profiles.sql
-- Warehouse, base, schema y la tabla de perfiles de negocio (encuesta de
-- onboarding). Todo es IF NOT EXISTS, así que correrlo dos veces no hace daño.
-- Las columnas tienen que cubrir TODOS los campos de BusinessProfile
-- (backend/app/models/schemas.py): si falta alguna, el POST responde
-- {"status":"ok"} pero ese campo se pierde en silencio y el GET lo regresa como
-- null. El test tests/test_business_profile.py vigila eso.

CREATE WAREHOUSE IF NOT EXISTS HACKMTY_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS HACKMTY;
CREATE SCHEMA IF NOT EXISTS HACKMTY.PUBLIC;

USE WAREHOUSE HACKMTY_WH;
USE DATABASE HACKMTY;
USE SCHEMA PUBLIC;

CREATE TABLE IF NOT EXISTS business_profiles (
  owner_id STRING PRIMARY KEY,
  category STRING,
  category_detail STRING,
  operating_days ARRAY,
  city STRING,
  employees STRING,
  answers VARIANT,
  week_description_mode STRING,
  week_description_text STRING,
  week_description_audio_base64 STRING,
  week_description_audio_mime STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Para quien creó la tabla con la versión corta de la guía: agrega lo que falte
-- sin tener que borrar nada.
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS category_detail STRING;
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS week_description_mode STRING;
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS week_description_text STRING;
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS week_description_audio_base64 STRING;
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS week_description_audio_mime STRING;
