# Capital One Business — HackMTY 2026 (reto Capital One)

Inteligencia de flujo de efectivo y capital de trabajo para micro-negocios.
El dueño vende con QR y compra con su tarjeta de negocio; la app lleva sola el
inventario (recetas, costo promedio), la contabilidad de partida doble, los
estados financieros, las razones y un asistente que responde en lenguaje
natural con los datos reales del negocio. Una encuesta de 2 minutos perfila el
negocio y decide qué lección de educación financiera ("Cash Insight") ver.

> **Es una demo: todo el dinero es simulado.** No se procesa dinero real, no se
> conecta a cuentas bancarias reales y los cobros por QR usan un proveedor de
> pago de prueba. Tampoco es un producto de Capital One (ver
> [Créditos y transparencia](#créditos-y-transparencia)).

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
cd backend && ruff check . && pytest -q     # 295 tests, siempre en memoria/sqlite
cd frontend && npm run build && npm run e2e # 45 specs de Playwright × 2 proyectos
```

GitHub Actions (`.github/workflows/ci.yml`) corre en cada push a `main` y en
cada PR hacia `main` o `develop` tres jobs: `backend-test` (`ruff` + `pytest`), `frontend-build` y `e2e`
(Playwright en chromium). Ningún test necesita credenciales: el backend de
pruebas usa sqlite y los e2e simulan las respuestas del API.

Dos suites vale la pena mirar:

- **Preguntas doradas del asistente:** 50 preguntas con su respuesta y
  evidencia esperadas, en `backend/tests/golden/`. Cada una pasa además por un
  LLM tramposo que la guardia anti-alucinación debe detener.
- **Checklist OWASP API Security Top 10:** qué se cubre y con qué test, en
  [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md).

## De dónde salió este repo

El repo nació como base genérica antes de que HackMTY 2026 publicara la
rúbrica, apostando por el patrón de HackMTY 2025 (Capital One como sponsor y la
API Nessie). De esa etapa se conservan dos decisiones:

- **Cliente mock de Nessie desde el día 1.** En 2025 la API de Nessie se cayó a
  media competencia y no volvió. Aquí todo pasa por `Depends(get_nessie_client)`
  y `USE_MOCK_NESSIE=true` cambia al mock sin tocar la lógica.
- **CI desde el primer commit**, en vez de dejarlo para el final.

## Estado y hoja de ruta

- Estado verificado y lo que falta confirmar contra Snowflake real:
  [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).
- Plan de pulido post-hackathon: [`docs/ROADMAP_PULIDO.md`](docs/ROADMAP_PULIDO.md).
- **Alcance a propósito:** sigue siendo una demo con datos simulados. No mueve
  dinero real ni se conecta a bancos reales.
- **Rebranding condicional:** si este proyecto evoluciona más allá de ser la
  entrega de HackMTY 2026 (presencia pública sostenida, usuarios reales de forma
  continua, financiamiento), el nombre, el logo y la paleta se reemplazan por
  unos propios antes de ese paso.

## Si esto fuera un producto real: lo que ya pensamos y decidimos no construir en 36 horas

En un hackathon, cada hora que se va a una integración que el jurado no puede
ver es una hora que no llega al problema del dueño del negocio. Por eso estas
piezas se evaluaron y se dejaron fuera a propósito. Para cada una, el código
ya deja listo el punto donde entraría.

- **Bancos y pagos reales.** Nessie, el sandbox de Capital One, y el proveedor
  de pagos demo recorren el flujo completo sin mover un peso. Un producto real
  pondría Plaid o Finicity detrás de `NessieClient` (`backend/app/nessie/base.py`,
  que ya tiene su versión mock y la real de Nessie) y Stripe o Square detrás de
  `PaymentProvider` (`backend/app/finance/payments.py`). El webhook de ese
  proveedor construiría el mismo `PaymentEvent` que hoy arma el demo, y
  `get_payment_provider()` es el único lugar que cambia. No se integró porque
  exige cuentas verificadas y dinero de terceros, justo lo que esta demo no
  debe tocar.
- **OCR de tickets.** Hoy los tickets son de muestra (`SAMPLE_RECEIPTS`). Todo
  lo que viene después ya funciona: emparejar artículos con insumos, dar
  entrada al inventario y reclasificar la compra. Todo eso pasa por
  `PurchaseService.attach_receipt(..., source="sample")`. Un OCR sólo cambia de
  dónde llegan los renglones y el valor de `source`. Construirlo en 36 horas
  habría significado demostrar un modelo de visión en vez del producto.
- **Datos híbridos a escala.** Snowflake es la fuente de verdad, corre Cortex
  para el asistente y permite comparar negocios. Ese uso le queda bien. Pero
  no está hecho para miles de escrituras pequeñas por segundo con latencia
  baja. A escala, las tablas de alta frecuencia (órdenes, pagos, diario,
  movimientos de inventario) vivirían en una base OLTP y se replicarían a
  Snowflake para la analítica. La capa `Database` (sqlite y Snowflake detrás
  de la misma interfaz) es la costura para esa separación. Esta tensión se
  documenta y no se resuelve ahora: con el volumen de una demo no existe.
- **Multi-moneda.** Cada orden guarda su moneda (la panadería vende en USD y
  la estética en MXN), pero los libros de cada negocio suman en una sola
  moneda y la app muestra `$` para ambas. Aquí funciona porque los dos
  símbolos coinciden y ningún negocio mezcla monedas. Un producto real
  necesitaría tipos de cambio con fecha, una moneda funcional por negocio y
  reportes que no sumen pesos con dólares.
- **Cumplimiento regulatorio.** KYC/AML, PCI-DSS y licencias de transmisión de
  dinero son obligatorios el día que pase dinero real de terceros por la
  plataforma. Como la decisión de producto es que eso no pase, construir ese
  cumplimiento ahora sería trabajo sin objeto. Lo que sí se hizo es lo que una
  demo pública necesita: contraseñas con bcrypt, rutas con dueño, rate limiting
  y el checklist OWASP de [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md).

## Créditos y transparencia

- Todas las imágenes de la presentación (incluida la tarjeta de crédito y la
  fachada de oficina) fueron generadas con IA a partir de prompts que incluían
  "Capital One Business"; ninguna es una fotografía real, un render oficial ni
  un asset proporcionado por Capital One.
- Descripciones del proyecto listas para reutilizar (Devpost, LinkedIn,
  presentación), con el mismo aviso de demo y de no afiliación:
  [`docs/DESCRIPCIONES_PUBLICAS.md`](docs/DESCRIPCIONES_PUBLICAS.md).

---

*Capital One Business fue construido en 36 horas para el reto de Capital One en
HackMTY 2026. Es una demo: todas las transacciones son simuladas; no se procesa
dinero real ni se conecta a cuentas bancarias reales. No es un producto de
Capital One ni está afiliado, respaldado o patrocinado por Capital One, N.A. — el
nombre y la identidad visual se usan únicamente para describir honestamente el
reto para el que fue construido.*
