# Capital One Business — Estado del proyecto

**Fecha de esta versión:** 2026-09-14
**Commit auditado:** `96b3d6b` (`main`), más las correcciones sin commitear que
se describen en [Reconciliación y CI](#reconciliación-y-ci-2026-09-14)
**Cómo se obtuvo:** auditoría de la Fase 3 de [`ROADMAP_PULIDO.md`](./ROADMAP_PULIDO.md),
**sólo en modo mock/sqlite** (`USE_SNOWFLAKE=false`, `USE_MOCK_NESSIE=true`, sin
`backend/.env`, sin credenciales de Snowflake ni de Anthropic).
**Versión anterior:** [`archive/PROJECT_STATUS_2026-09-13.md`](./archive/PROJECT_STATUS_2026-09-13.md)
(se conserva tal cual; mezclaba notas de distintos momentos del hackathon).

Leyenda: ✅ verificado hoy en vivo · 🧪 cubierto por tests automatizados, no
recorrido a mano · ⏳ pendiente de verificar contra Snowflake real (Fase 9).

---

## En 30 segundos

- **Todo lo que se puede probar sin Snowflake funciona:** 151 tests de backend
  en verde (eran 119; se agregaron 14 de fechas y 18 de la Fase 5), `ruff`
  limpio, build del frontend OK, e2e de 40 specs × 2 proyectos (un `skip`
  intencional en móvil).
- **CI dependía del día en que corriera.** Había seis tests que pasaban o
  fallaban según la fecha real, y uno de ellos ya había puesto CI en rojo el
  2026-09-15. Ya se corrigieron; ver [Reconciliación y CI](#reconciliación-y-ci-2026-09-14).
- **El "hueco" que la versión anterior marcaba como a medias ya está cerrado
  en `main`:** la encuesta guarda `category` + `answers`, `App.tsx` los pasa a
  `Cuenta.tsx` y `CashInsightCard` aparece con la lección correcta
  inmediatamente después de "Ir a mi cuenta", sin recargar.
- **Lo que no se puede afirmar todavía:** que el sistema corre de punta a punta
  sobre Snowflake real. Hay evidencia indirecta de que la tabla de perfiles sí
  llegó a escribirse en una cuenta real, pero nada verificable hoy sobre el
  núcleo financiero. Queda anotado abajo para la Fase 9.

---

## Cómo se verificó

Máquina: Windows 11, Python 3.13 (no hay 3.12 instalado; CI usa 3.12), Node
24.14.1 / npm 11.12.1 (CI usa Node 20). `backend/.venv` y `frontend/node_modules`
se crearon desde cero para esta auditoría.

| Qué | Comando | Resultado |
|---|---|---|
| Lint backend | `cd backend && ruff check .` | ✅ `All checks passed!` |
| Tests backend | `cd backend && pytest -q` (con `USE_SNOWFLAKE=false`) | ✅ **119 passed** en ~51 s al auditar; **133 passed** tras las correcciones (warnings: `JWT_SECRET` efímero y un deprecation de starlette) |
| Build frontend | `cd frontend && npm run build` | ✅ OK (aviso de tamaño de chunk, no bloqueante) |
| E2E | `cd frontend && npm run e2e` | ✅ **57 passed, 1 skipped** (29 specs × 2 proyectos) al auditar; **63 passed, 1 skipped** (32 specs) tras la Fase 4; **40 specs** tras integrar las Fases 1 y 8 sobre la Fase 5 (CI en chromium: 40/40). Ver nota de intermitencia abajo |
| Stack en vivo | `python dev.py` (API :8000, web :5173) | ✅ arranca; `/health` → `{"storage":"memory","nessie_mode":"mock","payment_provider":"demo",...}`; siembra la demo al arrancar |
| Recorrido real sin stubs | script de Playwright contra el stack vivo (no está en el repo) | ✅ 8/8 pasos, detallados en la siguiente sección |

**Intermitencia e2e:** la *primera* corrida, con `node_modules` recién instalado,
dio 6 fallos en chromium (`auth.spec.ts` ×3, `card-flip.spec.ts` ×3). Los de
`card-flip` fueron timeouts esperando "¿Cómo te llamas?" justo después del
registro, con una recarga completa de Vite a mitad del test. Las dos corridas siguientes —una de ellas con
`node_modules/.vite` borrado a propósito— pasaron completas. No se reprodujo, así
que no hay causa confirmada. En CI quedaría tapado por `retries: 2`.

---

## Estado real por área

### Onboarding → Cuenta → Cash Insight ✅

Recorrido real (registro nuevo, sin `page.route`):

| Escenario | Resultado |
|---|---|
| Registro → encuesta *Belleza*, todo "No" → *Ir a mi cuenta* | Tarjeta "¿Cuánto te deja realmente una cita?" en Cuenta, **0 recargas**. El perfil local y el guardado en backend coinciden (`category=belleza`, 8 respuestas). |
| Registro → encuesta *Comida*, todo "Sí" | Gana el trigger de respuestas "No necesitas más inventario; necesitas mejor inventario" sobre el de categoría (el orden de `TRIGGERS` en `insights.js`). La microlección abre. |
| Cerrar y volver a entrar con esa cuenta | Entra directo a Cuenta con la misma tarjeta (perfil leído del backend). |

Hallazgos de la auditoría, **resueltos en la Fase 4 (2026-09-15)**:

- ~~La prioridad "dato real > sólo encuesta" no estaba en `insights.js` y en
  Cuenta nunca aparecía un insight de datos.~~ Ahora `pickBestTrigger(profile,
  dataInsights)` elige primero el insight de `/analytics/insights` y, sin datos,
  el de la encuesta. Cuenta lo aplica: una cuenta nueva ve la lección de su
  encuesta y las demos ven "Según tus datos".
- ~~Tarjeta duplicada en `/educacion`.~~ `pickSurveyTrigger` salta los triggers
  de encuesta cuyo tema ya cubre un insight de datos que está en pantalla.
- ~~No había un e2e de "termino la encuesta → la tarjeta correcta aparece sin
  recargar".~~ Lo cubre `e2e/cash-insight.spec.ts`: sin datos, con datos y
  Educación sin repetir tema.

Flujo trazado: `OnboardingFlow.jsx` → `onComplete({category, answers, name,
lastName})` → `App.setProfile` (estado + `sessionStorage`) → `BusinessProvider`
y `MainApp` → `<Cuenta profile>` → `CashInsightCard`. El login arma el mismo
perfil con `localProfileFrom`. `frontend/src/onboarding/Onboarding.jsx` es una
copia vieja de la encuesta que no importa nadie.

Verificado en vivo (sqlite/mock) el 2026-09-15:

| Cuenta | Cuenta muestra | ONE Education muestra |
|---|---|---|
| Nueva, comida y "Sí" a todo | encuesta: "No necesitas más inventario…" (sin recargar) | la misma lección (no hay datos) |
| `demo_panaderia` | datos: "Tu efectivo también se queda atrapado en el almacén" | datos (almacén, reorden) + encuesta: "¿El descuento al mayoreo realmente te ahorra dinero?" |
| `demo_estetica` | datos: "Tu efectivo también se queda atrapado en el almacén" | datos (almacén, reorden) + encuesta: "¿Cuánto te deja realmente una cita?" |

### Cuentas demo y "Explorar la demo" ✅

- `demo_panaderia` / `PanDeCadaDia2026` y `demo_estetica` / `BellezaConNumeros2026`
  entran por *Iniciar sesión* en un backend recién levantado, directo a Cuenta,
  con efectivo real, "Cómo va el negocio" y 8 movimientos; 0 errores en consola.
- *Explorar la demo → Panadería La Espiga* entra sin registro; *Análisis* abre
  con el resumen de apertura y los chips responden.

### Venta por QR y pago público ✅

Orden creada por API → página pública → *Pagar* → la orden queda `PAID`
(proveedor demo). La ruta del frontend es **`/#/pay/:token`** (`HashRouter`);
`/pay/{token}` es la ruta del API. Abrir `/pay/<token>` sin `#` muestra la
landing. El link que genera la app (`api/config.ts`) ya usa el `#`.

~~La página de pago no mencionaba que es una demo.~~ **Resuelto en las Fases 1
y 8 (2026-09-15):** en cualquier estado de la orden lleva al pie el aviso de
dinero simulado y el disclaimer de no afiliación.

### Transparencia: demo y no afiliación ✅

Fases 1 y 8, 2026-09-15. Los textos viven en un solo lugar,
`frontend/src/components/DemoNotice.tsx`.

| Superficie | Qué dice |
|---|---|
| Landing | Aviso de demo legible y disclaimer al pie, visibles desde el primer instante (fuera de la intro animada); se alcanza en un celular de 320×568 |
| Página de pago `/#/pay/:token` | Mismo pie en cualquier estado de la orden, además de "Pago de prueba" |
| Dentro de la app | Franja persistente "Modo demo — datos simulados" bajo los íconos de la barra inferior, con su alto reservado para no tapar contenido |
| Registro (bienvenida) | "Todas las transacciones son simuladas: no se procesa dinero real…" |
| `README.md` | Frase al inicio, "Estado y hoja de ruta" (rebranding condicional), "Créditos y transparencia" y disclaimer al pie |
| Fuera del repo | `docs/DESCRIPCIONES_PUBLICAS.md` para Devpost, LinkedIn y presentación (se pegan a mano); `og:description`, manifiesto PWA y `/docs` del API ya lo dicen |

Verificado con `e2e/demo-transparency.spec.ts`, que revisa cada superficie por
separado, y con capturas de la landing, la app y la página de pago.

**Decisión pendiente (no se tocó por el criterio de la Fase 1):**

- `frontend/public/logo-capital-one-business.jpeg` es prácticamente el
  logotipo real de Capital One (wordmark y swoosh) y sólo lo usa
  `onboarding/Logo.jsx`, que nadie importa.
- `components/CapitalOneLogo.tsx`, que sí se ve en la landing, la bienvenida y
  el pago, recrea el mismo swoosh a partir de `public/swoosh.svg`.

Es justo el riesgo (2) de la Fase 1: el logotipo real usado como asset gráfico.
Retirarlo o sustituirlo es decisión de Diego.

### Asistente 🧪 + ✅ puntual

Sin estado, una pregunta a la vez (confirmado). Con la estética y sin LLM:
"¿Cuándo se me acaba el tinte?" → respuesta con cifras; "¿y el esmalte?" →
respuesta de respaldo; "¿Cuándo se me acaba el esmalte?" → respuesta correcta.
Con sqlite y sin `ANTHROPIC_API_KEY` todo es plantilla determinista (no se
probó la redacción con LLM en esta auditoría).

### Núcleo financiero 🧪

Partida doble, inventario con costo promedio, estados financieros, compras
clasificadas, análisis y aislamiento por negocio: cubiertos por
`test_finance_engine.py`, `test_finance_api.py`, `test_assistant.py` y
`test_demo.py` contra sqlite en memoria, todos en verde. En vivo sólo se
recorrieron Cuenta, Análisis y la venta por QR; Compras, tickets, Inventario y
Libros no se recorrieron a mano hoy.

### Perfiles y usuarios 🧪

Con `USE_SNOWFLAKE=false` los perfiles viven en `MemoryProfileStore` (se pierden
al reiniciar) y el núcleo en sqlite en memoria. `test_snowflake_store_covers_all_profile_fields`
valida el SQL de `SnowflakeProfileStore` contra el esquema **sin conectarse**.

### Datos y seguridad del demo público 🧪 + ✅ en vivo

Fase 5, 2026-09-15. Todo en modo sqlite/mock.

| Punto | Estado |
|---|---|
| Audio de la encuesta | Fuera de la fila del perfil: tabla `onboarding_audio` (migración portable `005`) con `expires_at`; se borra a los `ONBOARDING_AUDIO_RETENTION_DAYS` días (7; `0` = no se guarda). Purga al arrancar y, como mucho, cada 10 min en el GET/POST del perfil. El GET nunca devuelve audio, ni el que quedó en filas viejas. `SnowflakeProfileStore` ya no lo lee y lo vacía al re-guardar un perfil |
| `JWT_SECRET` | Obligatorio con `ENVIRONMENT=production`: el backend no arranca sin él. `render.yaml` declara `ENVIRONMENT=production` y lo genera con `generateValue` |
| Rate limiting | Por IP, en memoria y por proceso: `/pay/{token}` 60/min, stats 30/min, `/demo/session`, `/auth/register` y `/auth/login` 20/min cada uno. 429 con `Retry-After` expuesto por CORS; el frontend dice cuánto esperar. Detrás de Render usa el último salto de `X-Forwarded-For` (`TRUST_PROXY_HEADERS=true`) |
| Consentimiento | Cada pregunta de la encuesta aclara que las respuestas se usan agregadas y anónimas (sólo con 5 o más negocios); la grabadora avisa que el audio se borra a los 7 días |

Verificado en vivo contra el stack real:

- `/pay` responde 429 en la petición 61.
- Tras 20 logins fallidos, la UI muestra "Intenta de nuevo en 45 s" con CORS real.
- Un registro nuevo ve los dos avisos.
- Un perfil guardado con audio no lo devuelve en el GET.

**Límites conocidos:**

- El contador es por proceso: con varios workers el límite efectivo se multiplica.
- En una red compartida (una sala con la misma IP pública) todos cuentan juntos.

---

## ⏳ Pendiente de verificar contra Snowflake real (Fase 9)

Nada de esto se intentó responder conectándose a la cuenta. Se cierra en la
Fase 9, reemplazando esta sección por el resultado verificado.

1. **¿`SnowflakeProfileStore` corrió alguna vez contra una cuenta Snowflake
   real?** La versión anterior de este documento decía las dos cosas: "nunca se
   ha probado contra una cuenta real" y, más abajo, "núcleo financiero verificado
   de punta a punta contra Snowflake real". Evidencia indirecta que ya está en
   el repo, sin conectarse: `snowflake-out/` (commit `702205e`, 2026-09-13)
   contiene un export de `HACKMTY.PUBLIC` con `BUSINESS_PROFILES` (5 filas),
   `USERS` (8) y `SCHEMA_MIGRATIONS` (2). Eso sugiere que los perfiles y
   usuarios sí se escribieron en una cuenta real en algún momento, **pero en ese
   export no está ninguna de las 16 tablas del núcleo financiero** (migraciones
   003/004). No se sabe si el export es anterior a esas migraciones o si nunca
   se aplicaron.
2. Que `python -m scripts.migrate` (y la aplicación automática al arrancar)
   deje las migraciones 001–004 aplicadas sin error.
3. El recorrido completo sobre Snowflake: registro → onboarding → venta por QR →
   compra con tarjeta, confirmado en Snowsight.
4. Las cifras de rendimiento que da `FINANCIAL_CORE.md` ("un panel completo
   tarda 2–4 s en Snowflake") y los ~10 s de la primera siembra de `DEMO.md`.
5. La redacción con Snowflake Cortex (`LLM_PROVIDER=auto` sin key de Anthropic).
6. `AUTO_SUSPEND` y tamaño de `HACKMTY_WH`.
7. **De la Fase 5:** que `005_onboarding_audio.sql` se aplique limpio. Es
   aditiva y, ojo, **también se aplica sola** en cuanto un backend con
   `USE_SNOWFLAKE=true` arranque con este código (Render despliega al hacer push
   a `main`).
8. **De la Fase 5:** correr `python -m scripts.purge_legacy_profile_audio`
   (primero sin `--apply`) para vaciar el audio que quedó en `business_profiles`.
9. **De la Fase 5:** en el servicio de Render, que `JWT_SECRET` tenga valor
   (con `ENVIRONMENT=production` sin él no arranca) y que el rate limiting vea
   IPs distintas detrás del proxy.

---

## Otros hallazgos de la auditoría (sin corregir)

- **Todos los e2e simulan el backend** con `page.route()`. Ningún test
  automatizado ejercita el contrato real frontend ↔ backend; en esta auditoría
  sólo lo cubrió el recorrido manual.
- **`frontend/dev-dist/` está versionado pero se regenera** con cada
  `npm run dev` (plugin PWA), así que ensucia `git status` tras levantar el
  frontend. Los cambios generados en esta auditoría se revirtieron.
- **"Este mes" en la demo tiene dos bordes de calendario.** Las pantallas y el
  asistente usan "del día 1 a hoy" contra el periodo anterior del mismo largo:
  - el día 1 de un mes que cae en lunes (la panadería no abre), las ventas del
    mes van en $0;
  - el 31 de octubre de 2026, "¿Por qué bajó mi utilidad este mes?" encuentra
    la utilidad de la panadería **arriba** (+$45.57): al comparar el mes
    completo contra los 31 días anteriores, la caída de las últimas dos semanas
    se diluye. De 61 días medidos (septiembre y octubre de 2026) fue el único;
    el 31 de diciembre no pasa.

  No es un error del motor y el guion no depende de eso, pero conviene saberlo
  si se comparte la demo en esas fechas.

---

## Reconciliación y CI (2026-09-14)

Cambios sin commitear, hechos después de la auditoría.

### Tests que dependían de la fecha

La historia demo termina "hoy" y varios tests comparaban contra "esta semana" o
"este mes", así que el mismo commit podía pasar CI un día y fallar el siguiente.
Ya pasó: la corrida del 2026-09-15 falló en `test_demo_seed_is_financially_coherent`
y `96b3d6b` sólo subió existencias iniciales, lo que arreglaba ese día pero no
los demás. Se corrió la suite completa con el reloj simulado (`freezegun`, sólo
en el venv local) en unas 20 fechas: todos los días de la semana, inicios y
fines de mes, fin de año y 29 de febrero.

| Test | Cuándo fallaba | Corrección |
|---|---|---|
| `test_finance_engine.py::test_demo_seed_is_financially_coherent` | 12 de 21 fechas entre el 10 y el 30 de septiembre: la caja para pastel (que nunca se resurte) y el chocolate quedaban en negativo | **Código:** `Pipeline.producible()` en `finance/demo.py` recorta cada venta sembrada a lo que la existencia alcanza a producir. Cuando alcanza para todo no cambia nada (las cifras de `test_bakery_seed_is_reproducible` siguen iguales). Nuevo `test_demo_seed_never_leaves_negative_stock`: las dos demos × 7 fechas seguidas |
| `test_assistant.py::test_structured_answers_use_engine_numbers` | Todos los lunes: la semana en curso no tiene ventas | Pregunta por la semana pasada |
| `test_assistant.py::test_assistant_is_scoped_to_its_business` | El día 1 de un mes que cae en lunes | Compara contra el mes pasado |
| `test_finance_api.py::test_demo_session_provisions_seeded_bakery` | El día 1 de un mes que cae en lunes | Ventas de los últimos 30 días |
| `test_assistant.py::test_profit_drivers_explain_the_seeded_story` | El 31 de octubre de 2026 (el único de 61 días medidos) | Siembra y pregunta con fecha fija: prueba la historia, no el calendario |
| `test_auth.py::test_minor_cannot_register` | Cualquier 29 de febrero (`replace(year=…)` no existe) | `timedelta` en vez de `replace` |

### Documentos reconciliados

| Documento | Qué decía | Qué se cambió |
|---|---|---|
| `README.md` | Plantilla pre-hackathon ("no había publicado aún la rúbrica", Tauri "pruébenlo esta noche"); CI "lint + tests" | Reescrito: producto primero, enlaces a la documentación (incluido `ANALISIS_PROFUNDO.md`, arriba), arquitectura real, quick start con `dev.py`, los tres jobs de CI y la historia del repo. Sin disclaimers: son de las Fases 1 y 8 |
| `docs/CONTRIB.md` | 7 tests backend, 4 e2e; "los tests escriben en Snowflake real" con `USE_SNOWFLAKE=true`; "3.13+ no compila"; `GEMINI_API_KEY` "para insights" | Cifras actuales, qué cubren los e2e, que los tests **nunca** tocan Snowflake (`conftest.py` sustituye los stores), 3.13 funciona, `GEMINI_API_KEY` no se usa |
| `docs/RUNBOOK.md` | "No hay endpoint que diga si usa Snowflake o memoria"; tests lentos = Snowflake real; 3.13 no compila | `/health` sí trae `storage`; filas nuevas para tests lentos y fallas de CI por fecha; 3.14 es la versión sin wheels |
| `docs/DEV.md` | "Estado actual del venv en esta máquina" (un venv roto concreto); "3.12, NO 3.13+" | Sección genérica de diagnóstico; 3.13 funciona |
| `docs/DEMO.md` | "¿Cuándo se me acaba el tinte?" → "¿y el esmalte?" | Pregunta completa; el asistente no guarda contexto |
| `AGENTS.md` | Pantalla `Analisis` (ya no existe); "cuando el equipo decida la idea final…" | Árbol de pantallas y carpetas actual; sección de piezas heredadas (`services/insights.py`, `data/mock.ts`, routers de Nessie) |
| `backend/tests/conftest.py` | Docstring: "con USE_SNOWFLAKE=true escriben en la tabla real" | Corregido: los stores siempre son de memoria |
| `docs/ROADMAP_PULIDO.md` | §4 con premisa ya resuelta; §7 "119 backend" | Nota de actualización en §3 y §4 (tareas intactas); 133 backend |
| Versión anterior de este archivo | "A medias", rama `feature/financial-literacy`, "113 + 25" y "119 + 29" en el mismo documento, prioridades de Gemini y Vultr | Archivada en `archive/` y reemplazada |

Sin tocar a propósito:

- `docs/ANALISIS_PROFUNDO.md`. La Fase 2 pide no reescribir sus hallazgos,
  aunque atribuye a `SNOWFLAKE_SETUP.md` y `FINANCIAL_CORE.md` la frase
  "verificado de punta a punta contra Snowflake real", que sólo estaba en la
  versión anterior de este archivo.
- `docs/LLM_PROJECT_CONTEXT_PROMPT.md` y `snowflake-out/`. Son capturas de un
  momento: su lista de observaciones es histórica.
- La afirmación de rendimiento de `docs/FINANCIAL_CORE.md` (2–4 s por panel en
  Snowflake), que queda para la Fase 9.

---

## Qué cambia para las siguientes fases

- **Fase 4:** hecha (ver arriba). Consecuencia para el guion: las dos demos
  muestran hoy la **misma** tarjeta de datos en Cuenta (inventario atorado), y la
  lección propia de cada giro quedó en ONE Education. `DEMO.md` ya lo refleja.
- **Fases 1 y 8:** hechas (ver "Transparencia"). Pendiente de Diego: decidir qué
  hacer con la réplica del logotipo y pegar las descripciones públicas en Devpost,
  LinkedIn y la presentación.
- **Fase 5:** hecha (ver "Datos y seguridad del demo público"). Lo que queda
  para la Fase 9 está en los puntos 7–9 de la lista de pendientes.
- **Fase 9:** la lista de pendientes de arriba.

---

## Cómo reproducir esta auditoría

```powershell
# Backend (3.12 como CI; 3.13 también funcionó)
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt ruff
cd backend; $env:USE_SNOWFLAKE="false"; $env:USE_MOCK_NESSIE="true"
.venv\Scripts\ruff check .; .venv\Scripts\python -m pytest -q; cd ..
# Para simular otra fecha: pip install freezegun y un plugin de pytest que
# arranque freeze_time(FECHA, tick=True) en pytest_configure

# Frontend
cd frontend; npm ci; npx playwright install chromium
npm run build; npm run e2e; cd ..

# Stack en vivo (sin backend/.env queda en memoria/sqlite + mocks)
python dev.py
# Después: git checkout -- frontend/dev-dist   (lo regenera vite)
```

Recorrido manual que se hizo sobre el stack vivo: registro con encuesta
Belleza/"No" y Comida/"Sí", volver a iniciar sesión, login con las dos cuentas
demo (Cuenta + `/educacion`), *Explorar la demo* → Análisis → un chip, y venta
por QR pagada desde `/#/pay/:token`.

## Dónde está todo

- Guion de demo: [`DEMO.md`](./DEMO.md) · arquitectura del núcleo:
  [`FINANCIAL_CORE.md`](./FINANCIAL_CORE.md) · análisis completo:
  [`ANALISIS_PROFUNDO.md`](./ANALISIS_PROFUNDO.md)
- Correr local: [`DEV.md`](./DEV.md) · setup y variables: [`CONTRIB.md`](./CONTRIB.md) ·
  incidencias: [`RUNBOOK.md`](./RUNBOOK.md) · despliegue en Render: [`DEPLOY.md`](./DEPLOY.md)
- Snowflake real: [`SNOWFLAKE_SETUP.md`](./SNOWFLAKE_SETUP.md) (Fase 9)
- Plan de pulido: [`ROADMAP_PULIDO.md`](./ROADMAP_PULIDO.md)
