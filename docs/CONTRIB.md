# CONTRIB — como trabajar en este repo

Generado a partir de `frontend/package.json`, `backend/requirements.txt`,
`.env.example` y `frontend/.env.example`. Si cambian un script o una variable
de entorno, este archivo se regenera con `/update-docs` — no lo editen a mano
esperando que sobreviva.

Para desplegar y para incidencias en vivo, vean [RUNBOOK.md](./RUNBOOK.md).

## Requisitos

| Herramienta | Version | Por que esa |
|---|---|---|
| Python | **3.12.x** | CI corre 3.12. 3.13 también instala y pasa los tests (verificado en Windows, 2026-09-14); 3.14 no se ha probado y los pins (`pydantic==2.9.2`) no traen wheels para esa versión. |
| Node | 20 | Es la que usan los jobs `frontend-build` y `e2e` del CI. |

⚠️ **Un solo interprete por venv.** Si crean `.venv` con un Python y luego
corren `venv` otra vez encima con otro (por ejemplo el de MSYS2/Git Bash), el
directorio queda con dos layouts (`Scripts/` + `lib/python3.x/`) y `pyvenv.cfg`
apuntando al ultimo. El sintoma es desesperante: el mismo comando funciona en
una terminal y da `ModuleNotFoundError: No module named 'fastapi'` en otra. Si
les pasa, borren `.venv` y reconstruyanlo de cero.

## Setup

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example .env            # queda en backend/.env — ver la nota de abajo
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

⚠️ **El `.env` va en `backend/.env`, no en la raiz del repo.** `config.py` usa
`env_file=".env"`, que se resuelve **relativo al directorio actual**. Si lo
dejan en la raiz y corren uvicorn desde `backend/`, pydantic no lo encuentra,
no falla, y arrancan en modo memoria sin darse cuenta. Por la misma razon,
**uvicorn siempre se corre desde `backend/`**.

### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Por default el frontend le pega a `http://localhost:8000`. Para apuntar a otro
backend, copien `frontend/.env.example` a `frontend/.env.local` y definan
`VITE_API_URL`.

### Windows / PowerShell

PowerShell no tiene el prefijo `VAR=valor comando` de bash — es un error de
sintaxis. Las variables se setean aparte:

```powershell
$env:USE_MOCK_NESSIE = "true"
.\.venv\Scripts\python.exe -m pytest -q
```

Tampoco usen `curl` para probar la API: en PowerShell es un alias de
`Invoke-WebRequest` y no entiende `-d`. Usen `curl.exe`, `Invoke-RestMethod`,
o Git Bash.

## Scripts disponibles

Fuente: `frontend/package.json`. Se corren desde `frontend/`.

| Script | Comando | Que hace |
|---|---|---|
| `npm run dev` | `vite` | Dev server con HMR en el puerto 5173 (fijo, `strictPort`). |
| `npm run build` | `tsc -b && vite build` | Typecheck + build de produccion a `dist/`. Tambien genera el service worker de la PWA. |
| `npm run preview` | `vite preview` | Sirve el `dist/` ya construido, para revisar el build real. |
| `npm run typecheck` | `tsc -b --noEmit` | Solo tipos, sin generar archivos. |
| `npm run e2e` | `playwright test` | Los 45 specs x 2 proyectos (desktop + movil). Levanta el dev server solo. |
| `npm run e2e:ui` | `playwright test --ui` | Modo interactivo: se ve el navegador y se puede repetir paso por paso. |
| `npm run e2e:report` | `playwright show-report` | Abre el reporte HTML del ultimo corrida. |

El backend no tiene `package.json`; sus comandos son directos:

| Comando | Que hace |
|---|---|
| `pytest -q` | Corre los tests (desde `backend/`). |
| `ruff check .` | Lint. Es lo que corre el CI, correanlo antes de pushear. |
| `uvicorn app.main:app --reload` | Dev server con recarga automatica. |

## Variables de entorno

### Backend — `.env.example` → `backend/.env`

| Variable | Default | Para que |
|---|---|---|
| `NESSIE_API_KEY` | — | Key de la API de Nessie. Se saca en api.nessieisreal.com con login de GitHub. |
| `NESSIE_BASE_URL` | `http://api.nessieisreal.com` | Base de la API real. |
| `USE_MOCK_NESSIE` | `true` | `true` usa el cliente mock en memoria con la misma interfaz. Es el seguro contra que Nessie se caiga a media competencia, como paso en 2025. |
| `GEMINI_API_KEY` | vacio | Hoy no la usa nada (quedó del placeholder `services/insights.py`). |
| `ANTHROPIC_API_KEY` | vacio | Opcional. Con key, el asistente redacta con Anthropic; sin key, Cortex (si `USE_SNOWFLAKE=true`) o plantillas. |
| `CORS_ORIGINS` | `http://localhost:5173` | Origenes permitidos, separados por coma. **Sin diagonal final** o el navegador bloquea todo. |
| `USE_SNOWFLAKE` | `false` | `false`: perfiles y usuarios en memoria, núcleo financiero en sqlite. `true`: todo en Snowflake real. |
| `SNOWFLAKE_ACCOUNT` | vacio | Account Identifier, formato `ORG-CUENTA`. **Sin** `.snowflakecomputing.com`. |
| `SNOWFLAKE_USER` | vacio | Usuario de Snowsight. |
| `SNOWFLAKE_PASSWORD` | vacio | Password. Nunca en git ni en el chat del equipo. |
| `SNOWFLAKE_WAREHOUSE` | vacio | `HACKMTY_WH` segun [SNOWFLAKE_SETUP.md](./SNOWFLAKE_SETUP.md). |
| `SNOWFLAKE_DATABASE` | vacio | `HACKMTY`. |
| `SNOWFLAKE_SCHEMA` | vacio | `PUBLIC`. |
| `SNOWFLAKE_ROLE` | vacio | `ACCOUNTADMIN` para el hackathon; `HACKMTY_APP` (minimo privilegio) desde la Fase 9, ver [SNOWFLAKE_SETUP.md](./SNOWFLAKE_SETUP.md#rol-de-mínimo-privilegio-fase-9). |
| `ENVIRONMENT` | `development` | `production` en el servicio desplegado: ahi `JWT_SECRET` es obligatorio y el backend no arranca sin el. |
| `ONBOARDING_AUDIO_RETENTION_DAYS` | `7` | Dias que se conserva el audio de "narra tu semana" (tabla `onboarding_audio`); despues se borra solo. `0` = no se guarda. |
| `RATE_LIMIT_ENABLED` | `true` | Limite por IP en rutas publicas (`/pay`, stats, `/demo/session`, `/auth`). Ver `app/ratelimit.py`. |
| `TRUST_PROXY_HEADERS` | `false` | `true` solo detras de un proxy de confianza (Render): toma la IP real del ultimo salto de `X-Forwarded-For`. |
| `MAX_REQUEST_BODY_BYTES` | `3000000` | Tope al cuerpo de cualquier peticion; 413 si se pasa. Alcanza para el audio de la encuesta. |
| `ENABLE_LEGACY_NESSIE_ROUTES` | vacio | Rutas `/accounts/...` de la plantilla original. Vacio = encendidas en desarrollo y 404 en produccion; `true`/`false` lo fuerza. |
| `SENTRY_DSN` | vacio | DSN del proyecto Python/FastAPI en Sentry (capa gratuita). Vacio = errores solo en el log, con `error_id`. Nunca manda cuerpos, headers de auth, query strings ni el token del QR. |
| `RELEASE` | vacio | Version reportada con cada error; si esta vacio se usa `RENDER_GIT_COMMIT`. |

`USE_SNOWFLAKE=true` requiere ademas que la tabla tenga **todas** las columnas
de `BusinessProfile` — ver el `ALTER TABLE` en `SNOWFLAKE_SETUP.md`.

### Frontend — `frontend/.env.example` → `frontend/.env.local`

| Variable | Default | Para que |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | URL del backend. Vite la **hornea en el build**, asi que cambiarla exige rebuild, no basta reiniciar. |
| `VITE_SENTRY_DSN` | vacio | DSN del proyecto React en Sentry. Vacio = el SDK ni se descarga (import dinamico). Tambien se hornea en el build. |

## Tests

### Backend — `pytest`

```bash
cd backend && pytest -q          # 295 tests (antes de los de fechas y las Fases 5 a 7 y 11, CI tardaba ~16 s; en una laptop ~2 min)
```

**Los tests nunca tocan Snowflake**, aunque `backend/.env` tenga
`USE_SNOWFLAKE=true`: `tests/conftest.py` sustituye los stores de usuarios y
perfiles por los de memoria y la base del núcleo por sqlite en memoria, y
ningún test levanta el `lifespan` que siembra las demos. Aun así, las pruebas
de perfiles usan categorias inventadas (`test_categoria`, `stats_test`); si
agregan tests que guarden perfiles, respeten esa convencion.

La mayor parte del tiempo se va en `test_demo.py`, que siembra las dos demos
varias veces, incluida una semana completa de fechas simuladas: la historia
termina "hoy", así que sin ese test CI podía pasar o fallar según el día.

**Preguntas doradas del asistente** (`tests/test_assistant_golden.py`): los
casos viven en `tests/golden/asistente_preguntas_doradas.json`. Cada uno fija
la intencion, el idioma y la evidencia esperada, y recalcula sus cifras con el
motor. Ademas pasa por un LLM tramposo que la guardia anti-alucinacion debe
detener. Para cubrir una pregunta nueva basta con agregarla al JSON. Si se
agrega una herramienta al asistente sin preguntas doradas, un test falla.

**Checklist OWASP** (`tests/test_owasp_api.py`, detalle en
[SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md)). Incluye un guard
estructural: una ruta nueva que no este en la lista de publicas y no pida token
rompe CI.

`test_snowflake_store_covers_all_profile_fields` compara el SQL del store
contra `BusinessProfile.model_fields` **sin conectarse a Snowflake**. Si
agregan un campo al schema y se les olvida la columna, ese test truena — que
es justo lo que queremos, porque el sintoma real es silencioso (el POST
responde `ok` y el campo se pierde).

### Frontend — Playwright

```bash
cd frontend && npm run e2e       # 45 specs x 2 proyectos (1 skip en movil: hover)
```

Los tests **no necesitan backend**: interceptan con `page.route()` las
llamadas a `/auth/*`, `/business-profile/*`, `/demo/session` y las de
`/business/{id}/...` que leen las pantallas. Son deterministas, no escriben en
Snowflake, y corren en CI sin credenciales (CI sólo corre el proyecto
`chromium`). Cubren registro y login, la encuesta (happy path, 500, sin
conexión, reintento), el Cash Insight después de la encuesta (sin recargar, y
con prioridad de los insights de datos), los avisos de demo y de no afiliación
(landing, página de pago, franja dentro de la app), los avisos de consentimiento
y de retención del audio en la encuesta, el mensaje de un 429 en el login, login
de una cuenta existente, el
selector de demos, la tarjeta que se voltea y la bienvenida. La contracara: ningún e2e ejercita el
contrato real frontend ↔ backend.

Cuando agreguen tests, usen selectores por **rol y texto visible**
(`getByRole("button", { name: "Continuar" })`), no por clase CSS: las clases
cambian cuando se retoca el diseño y romperian los tests sin que nada este mal.

## Flujo de trabajo

1. Rama desde `main`: `git checkout -b feature/lo-que-sea`.
2. Antes de pushear, corran lo que corre el CI:
   ```bash
   cd backend && ruff check . && pytest -q
   cd ../frontend && npm run build && npm run e2e
   ```
3. PR a `main`. El CI corre tres jobs: `backend-test`, `frontend-build` y `e2e`.

## Reglas del proyecto

Las de fondo viven en [`AGENTS.md`](../AGENTS.md) y siguen vigentes. Las dos
que mas se rompen:

- **Nunca llamen `httpx` directo** desde un router o servicio — siempre
  `Depends(get_nessie_client)`. Es lo que permite cambiar a mock con una sola
  variable si Nessie se cae.
- **Nada sensible hardcodeado.** Todo a `.env`, y `.env.example` se mantiene
  con las llaves vacias — es una plantilla, no el archivo de alguien.
