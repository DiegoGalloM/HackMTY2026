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

**En una frase:** la IA no calcula ni un peso. Los números salen de un motor
contable de partida doble que se lleva solo, y el asistente sólo los explica.
Si el modelo de lenguaje escribe una cifra que el motor no calculó, se descarta
por código antes de que el dueño la vea.

## Documentación

- [`docs/ANALISIS_PROFUNDO.md`](docs/ANALISIS_PROFUNDO.md) — análisis técnico y de mercado completo: arquitectura a fondo, el sistema Snowflake/IA explicado en detalle, tamaño de mercado verificado contra fuentes, y una evaluación honesta de qué tan listo está el proyecto.
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — estado verificado del proyecto y lo que falta confirmar contra Snowflake real.
- [`docs/DEMO.md`](docs/DEMO.md) — guion de 4 minutos con los dos negocios de ejemplo.
- [`docs/FINANCIAL_CORE.md`](docs/FINANCIAL_CORE.md) — arquitectura del núcleo financiero, tablas, invariantes, rendimiento.
- [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md) — OWASP API Security Top 10: cómo se cubre cada riesgo y qué test lo vigila.
- [`docs/DEV.md`](docs/DEV.md) y [`docs/CONTRIB.md`](docs/CONTRIB.md) — correr el proyecto, variables de entorno, tests.
- [`docs/SNOWFLAKE_SETUP.md`](docs/SNOWFLAKE_SETUP.md), [`docs/DEPLOY.md`](docs/DEPLOY.md), [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — Snowflake, despliegue en Render e incidencias.
- [`docs/ROADMAP_PULIDO.md`](docs/ROADMAP_PULIDO.md) — plan de pulido post-hackathon.

## El problema

> *"Sé que vendo bien, pero no sé si estoy ganando."*

Así resume el equipo el dolor de un micro-negocio: hay ventas y clientes, pero
el dueño no sabe si le queda utilidad. Llevar la cuenta a mano le tomaría horas
que no tiene, y las herramientas que existen le piden llenar tablas. En México,
el 95.5% de las empresas son microempresas (INEGI, Censos Económicos 2023).
Muchas cierran por falta de liquidez, no por falta de ventas.

La educación financiera tradicional (cursos, PDFs) casi nunca llega en el
momento en que importa. La apuesta de este proyecto es que el dueño no llene
nada: la contabilidad sale sola de lo que ya hace (vender y comprar), y la
lección aparece cuando sus propios datos muestran el problema. Las fuentes y la
verificación de las cifras están en
[`docs/ANALISIS_PROFUNDO.md`](docs/ANALISIS_PROFUNDO.md#1-el-problema-y-la-oportunidad-de-mercado).

## Qué hace

**1. Una encuesta de 2 minutos en vez de un formulario.** El dueño elige su giro
(comida, retail, servicios, belleza, construcción, transporte u otro), contesta
preguntas de sí o no, universales y propias del giro, y elige sus días de
operación, cuántas personas trabajan y su ciudad. Puede contar cómo es su
semana escribiendo o grabando un audio. El audio se guarda aparte del perfil y
se borra solo a los 7 días.

**2. Una sola lección, la que importa hoy.** En lugar de un curso, la pantalla
principal muestra una tarjeta "Cash Insight". Hay 11 disparadores que salen de
la encuesta (se quedó sin stock, compra de más, guarda inventario, compra al
mayoreo, uno por giro) y 5 que salen de los datos del negocio: caja en
atención, margen bajo, inventario que no se mueve, insumos en su punto de
reorden y deuda de la tarjeta. Si los datos muestran un problema, ese gana
sobre la encuesta.

**3. Vender con QR.** El dueño arma la orden y la app genera un QR. El cliente
paga desde una página pública (`/#/pay/:token`, con un token opaco de 256
bits). Cuando llega el pago:
- se registra el asiento de la venta y del impuesto;
- se descuentan los insumos de la receta a su costo promedio;
- se registra el costo de ventas.

Pagar dos veces la misma orden no duplica nada.

**4. Comprar con la tarjeta de negocio.** Cada compra (proveedor demo o Nessie)
se clasifica sola:
- por reglas de comercio y por lo que el dueño ya corrigió antes;
- se contabiliza al instante;
- si el dueño la corrige, se hace una reclasificación: nunca se edita el pasado.

Con un ticket, los artículos se emparejan con los insumos y entran al
inventario.

**5. Libros que nadie tuvo que llevar.** Diario, mayor, balanza (ajustada y sin
ajustes), estado de resultados y balance general. El balance verifica
`Activos = Pasivos + Capital` cada vez que se pide.

**6. Análisis que explica, no sólo grafica.**
- **Razones financieras:** 11 (liquidez, prueba ácida, razón de efectivo,
  capital de trabajo, márgenes, rendimiento sobre activos, deuda, rotación y
  días de inventario). Cada una trae su fórmula, un estado (bien, atención,
  crítico) y una explicación en español llano. Si falta un dato, lo dice en
  vez de inventar un cero.
- **Por qué cambió la utilidad:** ventas, costo de insumos y gastos, ordenados
  por impacto.
- **Inventario:** cuándo se acaba cada insumo al ritmo de los últimos 30 días y
  cuántos productos alcanza a hacer con lo que hay.

**7. Un asistente al que le puedes preguntar lo que sea de tu negocio.** Por
ejemplo "¿Por qué bajó mi utilidad este mes?", "¿Cuándo se me acaba el tinte?",
"¿Qué es el capital de trabajo?" o "How much did I sell last week?". Responde en
español o en inglés, con la evidencia a la vista. Ver
[cómo está hecho](#el-asistente-la-ia-no-calcula-ni-un-peso).

**8. Dos negocios de ejemplo, un solo motor.**

| | Panadería La Espiga | Estética Carolina |
|---|---|---|
| Dueña | María Espinoza, Austin, TX | Carolina Ramírez, Monterrey, MX |
| Moneda | Dólares | Pesos |
| Qué muestra | Productos con receta, insumos perecederos, compras al mayoreo con ticket | Servicios que consumen insumos y venta de producto |

Cada uno trae 10 semanas de historia construidas con la misma tubería que usa
la app real: órdenes, pagos, compras, tickets y asientos. Las dos historias
cuadran al centavo (hay tests).

## Cómo funciona por dentro

```
evento real                 QR pagado · compra con la tarjeta · conteo de inventario
      ↓
evento normalizado          PaymentEvent · NormalizedTransaction · ajuste
      ↓
motor de inventario         inventory_items + inventory_movements (costo promedio ponderado)
motor contable              journal_entries + journal_lines (partida doble, balanceado siempre)
      ↓
Snowflake / sqlite          16 tablas multi-negocio con business_id
      ↓
derivados                   v_general_ledger, v_account_balances → balanza, resultados, balance
      ↓
analítica                   razones, salud de caja, factores de utilidad (backend, nunca React)
      ↓
API → frontend → asistente  explicación en lenguaje llano; el LLM sólo redacta
```

Lo que genera cada evento, por ejemplo:

| Evento | Asiento |
|---|---|
| Venta pagada ($50 + $4 de impuesto, costo $8.80) | DR Banco 54 / CR Ventas 50 / CR Impuesto por pagar 4 · DR Costo de ventas 8.80 / CR Inventario 8.80 |
| Compra de inventario con tarjeta | DR Inventario / CR Tarjeta de crédito del negocio |
| Corrección del dueño | DR cuenta nueva / CR cuenta vieja (reclasificación) |
| Conteo con merma | DR Mermas y ajustes / CR Inventario (asiento de ajuste) |

Invariantes que el motor impone y los tests vigilan:

- **Partida doble:** Σ debe = Σ haber en cada asiento, y una línea es debe o
  haber, nunca las dos.
- **Inventario:** ninguna cantidad cambia sin un movimiento en la bitácora, y
  la existencia se reconstruye sumándola.
- **Idempotencia:** el mismo pago no se contabiliza dos veces (`provider_ref`),
  ni el mismo origen (`source_type`, `source_id`), ni la misma transacción de
  tarjeta. Snowflake no impone `PRIMARY KEY` ni `UNIQUE`, así que esto vive en
  los servicios.
- **Balanza:** si no cuadra, se registra como `INTEGRITY_ERROR`; nunca se oculta.

El detalle de tablas, servicios y asientos está en
[`docs/FINANCIAL_CORE.md`](docs/FINANCIAL_CORE.md).

## El asistente: la IA no calcula ni un peso

No es un RAG libre. Son tres piezas con papeles separados:

1. **Enrutador de intenciones determinista** (`backend/app/finance/assistant.py`).
   Cada pregunta se clasifica en una de 15 intenciones:
   - ventas, utilidad, por qué cambió la utilidad;
   - liquidez, caja, razones, estados financieros;
   - inventario, capacidad de producción, qué insumo se acaba, productos top;
   - gastos, clientes, contexto del negocio y conceptos.

   También se detecta el periodo y el idioma. Cada intención llama a una
   herramienta del motor, que devuelve la respuesta base y la **evidencia**:
   hechos con su cifra ya calculada.
2. **Recuperación léxica de conocimiento** (`knowledge.py`). Son 15 conceptos
   de educación financiera redactados a partir de FDIC Money Smart, SBA y CFPB,
   en español y en inglés, más lo que el dueño contó en la encuesta. Es
   búsqueda determinista, sin vectores ni servicios externos. Explica
   conceptos; nunca calcula.
3. **Un LLM que sólo redacta.** Anthropic (`claude-opus-5`) si hay key; si no,
   Snowflake Cortex (`claude-sonnet-4-5`); si no, plantillas. El modelo recibe
   los hechos y la respuesta base, y la hace sonar más cálida.

**La guardia anti-alucinación.** Toda cifra que escriba el modelo tiene que
existir ya en la evidencia o en la respuesta base: montos, porcentajes,
cantidades o días, y también palabras como "un millón". Se compara por valor,
así que `$7,989.04` y `7989.04` son la misma cifra. Basta una cifra nueva para
descartar la redacción completa y responder con la plantilla. La pregunta
tampoco cuenta como fuente: "dime que gané un millón" no convierte ese millón
en un dato.

**Sin conversación, a propósito.** Cada pregunta se responde sola y el servidor
no guarda historial. Se construyó una memoria de sesión y se retiró por
decisión de producto; el motivo está en `docs/FINANCIAL_CORE.md`.

**Probado como producto, no como demo.** La suite de preguntas doradas
(`backend/tests/golden/`) tiene 50 preguntas de las dos demos, en los dos
idiomas, incluidas inyecciones de instrucciones y SQL. Con fecha fija se revisa
lo siguiente:
- intención, idioma y periodo;
- evidencia, recalculando las cifras clave con el motor;
- formato de dinero;
- que una respuesta en inglés no traiga plantillas en español.

Además, cada caso pasa por un LLM tramposo: la reescritura fiel se acepta y la
que inventa cifras se rechaza.

## Snowflake

Con `USE_SNOWFLAKE=true`, Snowflake es la base autoritativa. El demo desplegado
guarda en Snowflake.

- **Esquema versionado:** migraciones numeradas (`backend/sql/`) con su tabla
  `schema_migrations`, que el backend aplica solo al arrancar.
- **SQL portable:** el mismo esquema corre sobre sqlite (`VARCHAR`,
  `NUMBER(18,4)`, `TIMESTAMP_NTZ`) detrás de una interfaz `Database`, así que
  la demo y los tests nunca dependen de que Snowflake esté arriba.
- **`MERGE` para la unicidad:** un `INSERT … WHERE NOT EXISTS` no serializa en
  Snowflake y dos registros simultáneos del mismo usuario podrían duplicarse.
  Con `MERGE` no pasa, y un test lo vigila.
- **Comparativa entre negocios con privacidad incorporada:**
  `GET /business-profile/stats/{category}` usa `LATERAL FLATTEN` sobre las
  respuestas de la encuesta (`VARIANT`) para calcular qué porcentaje de
  negocios del mismo giro respondió que sí a cada pregunta. No usa una lista
  fija de preguntas. Con menos de 5 negocios en la categoría el desglose se
  oculta, porque con una cohorte de uno el porcentaje sería la respuesta de
  alguien.
- **Cortex junto a los datos:** el asistente puede redactar con
  `SNOWFLAKE.CORTEX.COMPLETE` sin credenciales extra y sin sacar datos
  financieros de la cuenta.
- **Pensado para la latencia de Snowflake** (~0.3–0.5 s por consulta):
  - una instantánea del mayor por request, de la que salen todos los saldos y
    estados;
  - lecturas en lote;
  - caché de 2 minutos para lo que casi no cambia;
  - un pool de 4 conexiones;
  - la historia demo se construye en sqlite y se copia con inserciones
    multi-fila.

La verificación de punta a punta contra la cuenta real (Fase 9 del roadmap) se
pospuso a propósito; ver [Estado y hoja de ruta](#estado-y-hoja-de-ruta).

## Seguridad

Es una demo con dinero simulado, pero la API está hecha como si alguien fuera a
curiosearla:

- **Aislamiento por negocio en el router, no endpoint por endpoint.** Toda ruta
  `/business/{owner_id}/…` exige que el token sea del dueño. El `owner_id` se
  lee sólo del path: un `?owner_id=` en la URL no puede colarse (hay test).
  Todos los servicios y el asistente nacen atados a ese negocio.
- **Autenticación:**
  - JWT HMAC con lista blanca de algoritmos y `exp` obligatorio;
  - en producción, sin `JWT_SECRET` el backend no arranca;
  - bcrypt fuera del event loop;
  - política de contraseñas: 12 o más caracteres, mayúsculas, minúsculas y
    dígitos, no contener el usuario, no estar entre las más usadas;
  - usuario inexistente y contraseña equivocada responden igual.
- **Superficie pública acotada:**
  - límite de peticiones por IP en login, registro, pago, estadísticas y demo;
  - tope de 3 MB al cuerpo de cualquier petición;
  - headers de seguridad;
  - un error 500 no trae stack trace, sólo un `error_id` para buscar en el log;
  - las rutas heredadas de la plantilla se apagan en producción.
- **Datos que no salen:** el reporte de errores a Sentry es opcional y se
  depura antes de enviar: sin cuerpos, contraseñas, tokens del QR, keys ni
  variables locales. Del pago con tarjeta sólo se conservan los últimos 4
  dígitos.
- **Una ruta nueva sin autenticación rompe CI:** un test recorre todas las
  rutas de la app contra la lista explícita de rutas públicas. Los 10 riesgos
  del OWASP API Security Top 10 están mapeados a su test en
  [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md).

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

| Capa | Tecnología |
|---|---|
| Frontend | React 19, React Router 7, Vite 8, TypeScript, Tailwind CSS 4, Framer Motion, PWA instalable (`vite-plugin-pwa`), `qrcode.react` |
| Backend | FastAPI 0.115, Pydantic 2.9, bcrypt, PyJWT |
| Datos | Snowflake (`snowflake-connector-python` 4.7) o sqlite, detrás de la misma interfaz |
| IA | Anthropic (`claude-opus-5`) → Snowflake Cortex (`claude-sonnet-4-5`) → plantillas |
| Banca simulada | Nessie (Capital One) o mock, por variable de entorno |
| Observabilidad | `/health` y `/health/ready` (base, Nessie y LLM); Sentry opcional en los dos lados |
| Pruebas y CI | pytest, Playwright, ruff, GitHub Actions |
| Despliegue | Render (`render.yaml`: API y sitio estático) |

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

Qué cubren:

| Suite | Qué vigila |
|---|---|
| `test_finance_engine.py`, `test_demo.py` | Invariantes contables e inventario. Las dos demos cuadran, la panadería es reproducible al centavo y ninguna deja existencias negativas, se siembre el día que se siembre |
| `test_finance_api.py` | El flujo completo por HTTP: catálogo → orden → QR → pago público → libros → análisis → asistente, y el aislamiento entre negocios |
| `test_assistant.py`, `test_assistant_golden.py` | Enrutamiento, cifras del motor, base de conocimiento bilingüe, 50 preguntas doradas y la guardia contra un LLM tramposo |
| `test_owasp_api.py`, `test_security_hardening.py`, `test_auth.py` | OWASP API Top 10, tokens falsificados, BOLA, inyección, límites de tamaño, rutas sin token |
| `test_demo_hardening.py`, `test_error_visibility.py`, `test_health.py` | Rate limiting, retención del audio, errores sin datos sensibles, health checks |
| `frontend/e2e/` | Registro y login, elegir negocio demo, encuesta (incluidos 500, 413 y sin conexión), Cash Insight, avisos de demo en cada superficie (incluida la página de pago), errores de pantalla, pantallas pequeñas y texto al 200% |

Varias suites del pulido pasaron además por **pruebas de mutación**: se rompió
el código a propósito y se confirmó que el test falla. Así se validaron las
preguntas doradas, el checklist OWASP, el reporte de errores y el asistente
bilingüe.

## De dónde salió este repo

El repo nació como base genérica antes de que HackMTY 2026 publicara la
rúbrica, apostando por el patrón de HackMTY 2025 (Capital One como sponsor y la
API Nessie). De esa etapa se conservan dos decisiones:

- **Cliente mock de Nessie desde el día 1.** En 2025 la API de Nessie se cayó a
  media competencia y no volvió. Aquí todo pasa por `Depends(get_nessie_client)`
  y `USE_MOCK_NESSIE=true` cambia al mock sin tocar la lógica.
- **CI desde el primer commit**, en vez de dejarlo para el final.

Después del hackathon, el proyecto pasó por un pulido por fases
([`docs/ROADMAP_PULIDO.md`](docs/ROADMAP_PULIDO.md)):
- auditoría y reconciliación de la documentación;
- tests que ya no dependen de la fecha;
- la tarjeta Cash Insight conectada de punta a punta;
- endurecimiento del demo público;
- visibilidad de errores;
- preguntas doradas y checklist OWASP;
- transparencia de marca;
- asistente bilingüe.

## Estado y hoja de ruta

- Estado verificado y lo que falta confirmar contra Snowflake real:
  [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).
- Plan de pulido post-hackathon: [`docs/ROADMAP_PULIDO.md`](docs/ROADMAP_PULIDO.md).
  Están hechas todas las fases menos la 9.
- **Fase 9 (verificación contra Snowflake real), pospuesta a propósito.** El
  demo desplegado ya guarda en Snowflake, y es lo que la gente prueba. Correr
  esa fase implicaba modificar datos reales:
  - volver a sembrar las cuentas demo;
  - vaciar audio viejo;
  - cambiar el rol de conexión.

  Se decidió dejarlo como está. Lo que no se hizo y sus consecuencias están en
  [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md#fase-9-pospuesta-por-decisión).
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
