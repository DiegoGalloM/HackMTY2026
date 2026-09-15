# RUNBOOK — operacion, incidencias y rollback

Que hacer cuando algo se rompe, sobre todo en vivo. Para correr el stack en el
dia a dia vean [DEV.md](./DEV.md); para el setup inicial,
[CONTRIB.md](./CONTRIB.md); para el deploy paso a paso,
[DEPLOY.md](./DEPLOY.md).

## Correr backend y frontend al mismo tiempo

Desde la raiz del repo, en **una sola terminal**:

```bash
python dev.py
```

Un solo Ctrl+C baja los dos. Banderas, setup y problemas comunes en
[DEV.md](./DEV.md).

## Antes de presentar (checklist de 5 minutos)

Corranlo **~5 minutos antes** de la demo, no en el momento:

```bash
curl https://<backend>.onrender.com/health     # despierta el contenedor (~50s si estaba dormido)
curl https://<backend>.onrender.com/business-profile/stats/comida   # despierta el warehouse
```

Los dos duermen por separado y se suman:

| Componente | Se duerme | Costo del arranque |
|---|---|---|
| Render (plan free) | ~15 min sin trafico | ~50 s |
| Snowflake `HACKMTY_WH` | `AUTO_SUSPEND = 60` s | ~5-10 s |
| Compute pool de SPCS (si lo usaran) | `autosuspend 300` s | varios minutos |

Frio + frio es alrededor de un minuto en el primer click. Es el detalle que
peor se ve frente a jueces y el mas facil de evitar.

## Deploy

El detalle esta en [DEPLOY.md](./DEPLOY.md). Resumen operativo:

1. Push a GitHub — Render despliega desde el repo, lo que no esta pusheado no existe.
2. Render lee `render.yaml` y levanta dos servicios: `hackmty2026-api` (FastAPI)
   y `hackmty2026-web` (build de Vite).
3. Las credenciales (`sync: false` en `render.yaml`) se capturan **solo** en el
   dashboard de Render. Nunca en el repo.
4. Las dos URLs se amarran despues del primer deploy:
   `VITE_API_URL` en el frontend, `CORS_ORIGINS` en el backend.

**`VITE_API_URL` se hornea en el build**: cambiarla exige *Manual Deploy* del
frontend, reiniciar no sirve de nada.

## Monitoreo

| Que | Donde |
|---|---|
| Backend vivo | `GET /health` → `{"status":"ok","nessie_mode":"mock\|real","storage":"memory\|snowflake","payment_provider":…,"transaction_provider":…}` |
| Logs del backend | Render → `hackmty2026-api` → Logs |
| Que consultas llegaron a Snowflake | Snowsight → Activity → Query History |
| Cuantos creditos van | Snowsight → Admin → Cost Management |
| Datos guardados | `SELECT * FROM business_profiles ORDER BY created_at DESC LIMIT 10;` |

`nessie_mode` en `/health` refleja Nessie; `storage` dice si el backend quedo
configurado con Snowflake (`USE_SNOWFLAKE=true` y cuenta definida) o en
memoria/sqlite. `storage` lee la configuracion, no prueba la conexion: para
confirmar que de verdad escribe, guarden un perfil y busquenlo en Snowsight.

## Problemas comunes

Todos estos ya nos pasaron. Ordenados por que tan seguido muerden.

| Sintoma | Causa | Solucion |
|---|---|---|
| `npm error ENOENT ... package.json` en la raiz | No hay package.json en la raiz; el proyecto Node vive en `frontend/` | `cd frontend && npm install` |
| El POST responde `{"status":"ok"}` pero el GET regresa los campos en `null` | La tabla de Snowflake no tiene todas las columnas de `BusinessProfile` | Corran el `ALTER TABLE` de [SNOWFLAKE_SETUP.md](./SNOWFLAKE_SETUP.md) |
| `invalid identifier 'CATEGORY_DETAIL'` | Lo mismo de arriba, pero explicito | Igual: `ALTER TABLE` |
| Guarda en memoria aunque `USE_SNOWFLAKE=true` | El `.env` esta en la raiz del repo, no en `backend/` | Muevanlo a `backend/.env` y reinicien uvicorn |
| Cambiaron `.env` y no pasa nada | `get_settings()` esta cacheado con `lru_cache`; `--reload` no basta | Reinicio real del proceso |
| El navegador bloquea todas las llamadas | `CORS_ORIGINS` con diagonal final, o sin el origen desplegado | Origen exacto, sin `/` al final |
| `ModuleNotFoundError: fastapi` en una terminal pero no en otra | `.venv` construido con dos interpretes distintos | Borrar `.venv` y rehacerlo con Python 3.12 |
| `pydantic-core` / `cffi` no compilan al instalar | Python 3.14+; los pins no tienen wheels para esa version | Usen Python 3.12 (el de CI); 3.13 tambien funciona |
| `USE_MOCK_NESSIE=true : The term ... is not recognized` | Sintaxis de bash en PowerShell | `$env:USE_MOCK_NESSIE = "true"` en una linea aparte |
| Primera llamada tarda ~1 min | Render y/o el warehouse dormidos | Normal. Despiertenlos antes (checklist de arriba) |
| `250001: Could not connect to Snowflake backend` | Account identifier mal escrito | Sin `.snowflakecomputing.com` al final |
| `Warehouse 'HACKMTY_WH' does not exist or not authorized` | Falto el Paso 3 del setup, o el rol no alcanza | Corran el Paso 3 completo y en orden |
| `pytest` tarda mas de un minuto en la laptop | `test_demo.py` siembra las demos varias veces (incluida una semana de fechas simuladas) | Es esperado; en CI tarda menos. Los tests nunca tocan Snowflake, aunque `backend/.env` tenga `USE_SNOWFLAKE=true` |
| CI falla un dia y al siguiente pasa sin cambios | Un test que depende de la fecha real (la historia demo termina "hoy") | Reproducirlo fijando la fecha (`monkeypatch.setattr(demo, "today", ...)`, como en `test_demo.py`) y volver el test independiente del dia |

### Si Nessie se cae

Paso en HackMTY 2025 a media competencia. Por eso existe el cliente mock:

```
USE_MOCK_NESSIE=true
```

Reinicien el backend y sigan. Ningun router ni servicio cambia, porque todo
pasa por `Depends(get_nessie_client)`.

### Si Snowflake se cae o se acaban los creditos

```
USE_SNOWFLAKE=false
```

La app sigue completa con los perfiles y usuarios en memoria y el nucleo
financiero en sqlite (las cuentas demo se vuelven a sembrar al arrancar). Se pierde la elegibilidad
del premio de Snowflake y los datos no sobreviven un reinicio, pero el producto
principal queda de pie. Es la misma idea que el mock de Nessie: un toggle, cero
cambios de codigo.

## Rollback

### Codigo

```bash
git revert <sha>          # preferido: deja historia
git push
```

Render redespliega solo al detectar el push. Si urge y no quieren esperar al
build: Render → servicio → Deploys → **Rollback** al deploy anterior, que ya
esta construido y tarda segundos.

### Variables de entorno

Render guarda historial de deploys pero **no** de variables. Si cambian
`CORS_ORIGINS` o `VITE_API_URL` y algo se rompe, no hay "deshacer": anoten el
valor anterior antes de tocarlo.

### Esquema de Snowflake

Agregar columnas es seguro y aditivo. Quitarlas **destruye los datos de esa
columna** y no se puede deshacer:

```sql
-- Solo si estan completamente seguros. No hay vuelta atras.
ALTER TABLE business_profiles DROP COLUMN <columna>;
```

Antes de cualquier cambio destructivo, saquen una copia — es una linea:

```sql
CREATE TABLE business_profiles_backup AS SELECT * FROM business_profiles;
```

Si borraron filas por accidente, Snowflake guarda el historial (Time Travel).
`business_profiles` tiene `DATA_RETENTION_TIME_IN_DAYS = 1`, o sea **un dia**
— verifiquenlo con `SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN TABLE business_profiles`:

```sql
SELECT * FROM business_profiles BEFORE (STATEMENT => '<query-id>');
```

El `<query-id>` sale de Query History en Snowsight.

## Contactos y recursos

- Setup de Snowflake: [SNOWFLAKE_SETUP.md](./SNOWFLAKE_SETUP.md)
- Deploy: [DEPLOY.md](./DEPLOY.md)
- Convenciones de codigo: [../AGENTS.md](../AGENTS.md)
- Estado del proyecto: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
