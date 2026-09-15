# Capital One Business — HackMTY 2026 (reto Capital One)

Inteligencia de flujo de efectivo y capital de trabajo para micro-negocios.
El dueño vende con QR y compra con su tarjeta de negocio; la app lleva sola el
inventario (recetas, costo promedio), la contabilidad de partida doble, los
estados financieros, las razones y un asistente que responde en lenguaje
natural con los datos reales del negocio. Una encuesta de 2 minutos perfila el
negocio y decide qué lección de educación financiera ("Cash Insight") ver.

Construido durante HackMTY 2026 para el track de Capital One (SMB Cash-Flow &
Working Capital Intelligence), con Nessie (el sandbox bancario de Capital One)
detrás de una interfaz intercambiable por un mock.

## Documentación

- [`docs/ANALISIS_PROFUNDO.md`](docs/ANALISIS_PROFUNDO.md) — análisis técnico y de mercado completo: arquitectura a fondo, el sistema Snowflake/IA explicado en detalle, tamaño de mercado verificado contra fuentes, y una evaluación honesta de qué tan listo está el proyecto.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — estado verificado del proyecto y lo que falta confirmar contra Snowflake real.
- [`docs/DEMO.md`](docs/DEMO.md) — guion de 4 minutos con los dos negocios de ejemplo.
- [`docs/FINANCIAL_CORE.md`](docs/FINANCIAL_CORE.md) — arquitectura del núcleo financiero, tablas, invariantes, rendimiento.
- [`docs/DEV.md`](docs/DEV.md) y [`docs/CONTRIB.md`](docs/CONTRIB.md) — correr el proyecto, variables de entorno, tests.
- [`docs/SNOWFLAKE_SETUP.md`](docs/SNOWFLAKE_SETUP.md), [`docs/DEPLOY.md`](docs/DEPLOY.md), [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — Snowflake, despliegue en Render e incidencias.
- [`docs/ROADMAP_PULIDO.md`](docs/ROADMAP_PULIDO.md) — plan de pulido post-hackathon.

## Arquitectura

```
┌──────────────────────┐   HTTP   ┌────────────────────────────┐
│ Frontend             │ ───────► │ Backend (FastAPI)          │
│ React + Vite (PWA)   │ ◄─────── │                            │
│ HashRouter, mobile   │          │ finance/  núcleo contable, │
└──────────────────────┘          │           inventario,      │
   /#/pay/:token: página          │           ventas QR,       │
   pública de cobro (QR)          │           análisis,        │
                                  │           asistente        │
                                  └──┬──────────┬──────────┬───┘
                                     │          │          │
                     ┌───────────────▼┐  ┌──────▼──────┐  ┌▼─────────────────────┐
                     │ Snowflake      │  │ Nessie API  │  │ Redacción del        │
                     │ o sqlite/      │  │ o mock      │  │ asistente: Anthropic,│
                     │ memoria (local)│  │             │  │ Cortex o plantillas  │
                     └────────────────┘  └─────────────┘  └──────────────────────┘
```

- **Los números salen del backend**, del diario contable y sus vistas; nunca de
  React ni del LLM, que sólo redacta con los hechos del motor.
- **Todo corre sin servicios externos:** con `USE_SNOWFLAKE=false` el núcleo
  usa sqlite en memoria, Nessie tiene un cliente mock con la misma interfaz y,
  sin key de LLM, el asistente responde con plantillas.
- El mismo build del frontend se puede empaquetar como app de escritorio con
  Tauri o Electron; [`desktop/README.md`](desktop/README.md) tiene la guía
  (no hay un empaquetado configurado en el repo).

## Quick start

Requisitos: Python 3.12 (el de CI; 3.13 también funciona) y Node 20+.

```bash
# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env            # los defaults ya funcionan sin Snowflake

# Frontend
cd ../frontend
npm install

# Los dos en una sola terminal, desde la raíz del repo
cd ..
python dev.py                      # API http://127.0.0.1:8000/docs · web http://localhost:5173
```

Para entrar sin registrarse: *Empezar* → *Explorar la demo*. Las cuentas
`demo_panaderia` / `PanDeCadaDia2026` y `demo_estetica` / `BellezaConNumeros2026`
también sirven en *Iniciar sesión*. Detalle en [`docs/DEV.md`](docs/DEV.md).

## Tests y CI

```bash
cd backend && ruff check . && pytest -q     # 151 tests, siempre en memoria/sqlite
cd frontend && npm run build && npm run e2e # 34 specs de Playwright × 2 proyectos
```

GitHub Actions (`.github/workflows/ci.yml`) corre en cada push a `main` y en
cada PR hacia `main` o `develop` tres jobs: `backend-test` (`ruff` + `pytest`), `frontend-build` y `e2e`
(Playwright en chromium). Ningún test necesita credenciales: el backend de
pruebas usa sqlite y los e2e simulan las respuestas del API.

## De dónde salió este repo

El repo nació como base genérica antes de que HackMTY 2026 publicara la
rúbrica, apostando por el patrón de HackMTY 2025 (Capital One como sponsor y la
API Nessie). De esa etapa se conservan dos decisiones:

- **Cliente mock de Nessie desde el día 1.** En 2025 la API de Nessie se cayó a
  media competencia y no volvió. Aquí todo pasa por `Depends(get_nessie_client)`
  y `USE_MOCK_NESSIE=true` cambia al mock sin tocar la lógica.
- **CI desde el primer commit**, en vez de dejarlo para el final.
