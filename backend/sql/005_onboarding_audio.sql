-- 005_onboarding_audio.sql
-- Audio de la encuesta ("narra tu semana") FUERA de business_profiles.
--
-- Es la voz de quien prueba el demo: un dato personal que no tiene por qué
-- quedarse para siempre en la fila del perfil. Aquí vive con fecha de
-- caducidad (expires_at) y el backend borra lo vencido (ver
-- app/storage/audio_store.py y ONBOARDING_AUDIO_RETENTION_DAYS).
--
-- Portable (sqlite + Snowflake), con las mismas reglas que 003: sólo
-- CREATE TABLE IF NOT EXISTS, tipos VARCHAR/TIMESTAMP_NTZ, sin defaults con
-- funciones. Es aditiva: no toca business_profiles.
--
-- El audio que ya existía en business_profiles NO se borra aquí, porque esta
-- migración se aplica sola al arrancar. Limpiarlo es un paso manual:
-- `python -m scripts.purge_legacy_profile_audio` (Fase 9).

CREATE TABLE IF NOT EXISTS onboarding_audio (
  owner_id      VARCHAR,
  audio_base64  VARCHAR,
  audio_mime    VARCHAR,
  created_at    TIMESTAMP_NTZ,
  expires_at    TIMESTAMP_NTZ
);
