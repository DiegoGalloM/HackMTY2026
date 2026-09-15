# Roadmap de pulido — Capital One Business

**Para:** una sesión de **Claude Code** sobre el repo `github.com/DiegoGalloM/HackMTY2026`
**De:** análisis post-hackathon (HackMTY 2026, track Capital One)
**Objetivo:** que el proyecto se vea, se lea y se navegue con la misma seriedad con la que se construyó — listo para enseñarlo ampliamente (LinkedIn, gente de Capital One en la red de Diego, reclutadores, colaboradores) — **sin volverlo un producto real que mueva dinero real.** Sigue siendo, a propósito, un demo con datos simulados; lo que se pule es la presentación, la documentación y las costuras técnicas visibles, no el alcance del producto.

---

## 0. Cómo usar este documento

Cada fase es un prompt independiente con su propio criterio de "terminado" — no hace falta pegar el documento completo de una sola vez. El orden importa (están numeradas por dependencia y por qué tan visible es el resultado, no por dificultad).

**Regla que aplica a TODAS las fases, sin excepción, y que debe repetirse al inicio de cada prompt que le des a Claude Code:**

> No ejecutes `git commit`, `git push`, ni abres pull requests bajo ninguna circunstancia. Termina el trabajo de la fase y deja los cambios sin commitear en el working tree. Yo reviso el diff, decido qué se queda, escribo mi propio mensaje de commit y abro el PR.

La sección 13, al final, explica cómo dejar esto asegurado más allá de un recordatorio en el prompt.

**Regla de secuencia: todo lo que toca Snowflake real va al final, en una sola fase dedicada (Fase 9).** Todas las demás fases se hacen y se prueban en modo mock/sqlite, sin que Claude Code necesite tus credenciales reales de Snowflake en ningún momento anterior a esa fase.

**Por qué Claude Code y no Codex:** el repo ya está instrumentado para Claude específicamente (`CLAUDE.md` con instrucciones de `graphify`, `.claude/skills/` con skills de diseño y branding, `AGENTS.md`), y gran parte del código ya lo construyeron agentes Claude durante el hackathon. Usar Claude Code aprovecha esa memoria de proyecto sin reconstruirla.

---

## 1. 🟡 Transparencia de marca — condicional, no bloqueante

El producto se llama "Capital One Business", usa la paleta de marca de Capital One y, en la presentación, imágenes generadas con IA que incluyen su identidad visual. Esto es correcto y esperado como entrega de un reto patrocinado por Capital One dentro de HackMTY. El riesgo real no está en nombrar la marca — está en (1) que el proyecto siga viviendo indefinidamente como producto público bajo ese nombre sin ninguna aclaración, (2) usar el logotipo real de Capital One como asset gráfico, y (3) cualquier framing que sugiera sociedad o aval oficial en vez de historia factual.

**Tarea para Claude Code:**

- Añadir un disclaimer de una línea, visible, en: pie del `README.md`, pantalla de bienvenida/landing (`frontend/src/landing/Landing.tsx`), y pie de la página pública de pago (`/pay/:token`). Texto sugerido:

  > *"Capital One Business fue construido en 36 horas para el reto de Capital One en HackMTY 2026. No es un producto de Capital One ni está afiliado, respaldado o patrocinado por Capital One, N.A. — el nombre y la identidad visual se usan únicamente para describir honestamente el reto para el que fue construido."*

- Añadir una sección "Créditos y transparencia" al `README.md`:

  > *"Todas las imágenes de la presentación (incluida la tarjeta de crédito y la fachada de oficina) fueron generadas con IA a partir de prompts que incluían 'Capital One Business'; ninguna es una fotografía real, un render oficial ni un asset proporcionado por Capital One."*

- Registrar en el README (sección "Estado y hoja de ruta") el disparador de un rebranding completo más adelante: *"Si este proyecto evoluciona más allá de ser la entrega de HackMTY 2026 — presencia pública sostenida, usuarios reales de forma continua, financiamiento — el nombre, el logo y la paleta se reemplazan por unos propios antes de ese paso."*

**Criterio de terminado:** disclaimer visible en los tres lugares, sección de créditos de imágenes en el README, nota de rebranding condicional registrada. Cero cambios de nombre, logo o dominio en esta fase.

---

## 2. 🔴 Reflejar el análisis profundo en el README

**Ya hecho por Diego a mano** (renombrado a `docs/ANALISIS_PROFUNDO.md` + enlace agregado en el README). Se deja documentada aquí para que el criterio de terminado quede registrado, no para volver a correrla con Claude Code:

**Criterio de terminado:** `docs/ANALISIS_PROFUNDO.md` existe en el repo con el contenido completo del análisis (sin reescribir hallazgos, cifras ni conclusiones), y el README enlaza a él de forma visible cerca del inicio. ✅

---

## 3. 🔴 Auditoría y reconciliación de la documentación

`docs/PROJECT_STATUS.md` describe piezas de UX "a medias", mientras que `docs/FINANCIAL_CORE.md` y `docs/DEMO.md` (fechados después) describen un sistema mucho más completo. Antes de tocar nada más, hay que saber cuál es el estado *real* del `main` actual.

**Todo esto se hace en modo mock/sqlite — nada aquí requiere tus credenciales reales de Snowflake.** Cualquier pregunta que sólo se pueda responder conectándose a la cuenta real de Snowflake se anota como pendiente y se resuelve en la Fase 9, al final.

**Tarea para Claude Code:**
- Levantar backend y frontend localmente con `USE_SNOWFLAKE=false` (`python dev.py`), correr `pytest -q` y `npm run e2e`, reportar qué pasa y qué no.
- Verificar en vivo si `Cuenta.tsx` ya recibe `category`/`answers` del perfil y si `CashInsightCard` ya se muestra (si no, es la Fase 4).
- Anotar como pendiente-para-Fase-9 la pregunta de si `SnowflakeProfileStore` corrió alguna vez contra una cuenta Snowflake real — no intentar responderla ahora conectándose a la cuenta.
- Producir un `docs/PROJECT_STATUS.md` actualizado con la fecha de hoy, archivando (no borrando) la versión anterior en `docs/archive/`, y dejando explícito qué quedó pendiente de verificar contra Snowflake real.

**Hecha (2026-09-14).** Resultado en `docs/PROJECT_STATUS.md`; la versión anterior quedó en `docs/archive/PROJECT_STATUS_2026-09-13.md`. De paso se reconciliaron las contradicciones entre documentos y se corrigieron dos tests que hacían que CI pasara o fallara según el día. ✅

---

## 4. 🔴 Cerrar el hueco de producto más visible

La encuesta de onboarding guarda `category` y `answers`, pero (según `PROJECT_STATUS.md`) `Cuenta.tsx` no los recibía como props, así que `CashInsightCard` no tenía con qué decidir qué mostrar.

> **Actualización tras la Fase 3 (2026-09-14):** en `main` esto ya funciona. `Cuenta.tsx` recibe el perfil y `CashInsightCard` muestra la lección correcta justo después de la encuesta, sin recargar (verificado en vivo). Además, la prioridad "dato real > sólo encuesta" **no** está en `insights.js`: los insights basados en datos vienen del backend (`/analytics/insights`) y sólo se muestran en `/educacion`. Lo que sigue pendiente de esta fase: el e2e de "termino la encuesta → aparece la tarjeta correcta", decidir si Cuenta debe preferir el insight de datos y quitar el título duplicado en `/educacion`. Detalle en `docs/PROJECT_STATUS.md`.

**Tarea para Claude Code:**
- Trazar el flujo desde `frontend/src/onboarding/OnboardingFlow.jsx` hasta `frontend/src/screens/Cuenta.tsx`, pasando por `frontend/src/business/BusinessContext.tsx`.
- Conectar `category` + `answers` al componente `CashInsightCard`, respetando la prioridad ya escrita en `frontend/src/financial-literacy/insights.js` (un trigger de datos reales tiene prioridad sobre uno de solo-encuesta).
- Añadir un test de Playwright que registre un negocio, complete la encuesta con una respuesta que dispare un trigger conocido, y verifique que la tarjeta correcta aparece sin recargar.
- Criterio de terminado: ese e2e pasa en CI, corriendo contra sqlite/mock.

**Hecha (2026-09-15).** La prioridad quedó escrita en `insights.js` (`pickBestTrigger`: insight de datos de `/analytics/insights` primero, encuesta después; `pickSurveyTrigger` salta los temas que ya cubren los datos). Cuenta la aplica y `/educacion` ya no repite temas. El e2e `frontend/e2e/cash-insight.spec.ts` registra, completa la encuesta y verifica la tarjeta sin recargar, con y sin insights de datos, contra el API simulado como el resto de la suite. También se verificó en vivo contra el backend en sqlite. ✅

---

## 5. 🟡 Cerrar costuras de datos y seguridad visibles en un demo público

Esto ya no es "para cuando haya usuarios reales" — es para que un demo que de verdad vas a compartir en LinkedIn no exponga datos personales ni tenga huecos obvios si alguien técnico entra a curiosear. **El código de esta fase se escribe y se prueba en modo mock/sqlite; la verificación de que funciona igual contra Snowflake real queda para la Fase 9.**

- **Sacar el audio del onboarding de la fila de Snowflake.** `week_description_audio_base64` guarda audio como base64 directo en una columna. Es un dato de voz personal de quien pruebe el demo; debería vivir en un bucket con su propia política de retención (o, más simple para un demo, simplemente no persistirlo más de X días). Escribe el cambio y su migración ahora; la migración se corre contra la cuenta real en la Fase 9.
- **`JWT_SECRET` fijo.** Si se deja vacío, se genera uno aleatorio al arrancar — invalida sesiones en cada deploy. Dejar el cambio de código (exigirlo cuando `ENVIRONMENT=production`); fijar el valor real en el entorno de despliegue es un paso manual de Diego, no de Claude Code.
- **Rate limiting en rutas públicas** (`/pay/{token}`, `/business-profile/stats/{category}`) — barato de agregar, evita que un enlace viral en LinkedIn se preste a abuso.
- **Consentimiento explícito para el benchmarking cross-negocio**, aunque sea sólo texto informativo en el onboarding ("estas respuestas, de forma agregada y anónima, ayudan a comparar tu categoría de negocio").

**Hecha (2026-09-15), en modo mock/sqlite.**

- **Audio.** Ya no se guarda en la fila del perfil. Vive en la tabla `onboarding_audio` (migración portable `005`, aditiva) con `expires_at` y se borra solo a los `ONBOARDING_AUDIO_RETENTION_DAYS` días (default 7; `0` = no se guarda). La purga corre al arrancar y, como mucho, cada 10 minutos en el GET o POST del perfil. El GET nunca devuelve audio. Limpiar el audio que ya existía en `business_profiles` es destructivo, así que **no** va en `backend/sql/`, que se aplica solo al arrancar con `USE_SNOWFLAKE=true`: es un paso manual de la Fase 9, `python -m scripts.purge_legacy_profile_audio --apply`.
- **`JWT_SECRET`.** Con `ENVIRONMENT=production` el backend no arranca sin él. `render.yaml` ya declara `ENVIRONMENT=production` y `JWT_SECRET` con `generateValue`. Paso manual de Diego: confirmar en el dashboard de Render que la variable tiene valor.
- **Rate limiting por IP.** Cubre `/pay/{token}` (GET y POST), `/business-profile/stats/{category}`, `/demo/session`, `/auth/register` y `/auth/login`. Responde 429 con `Retry-After`, expuesto por CORS, y el frontend dice cuánto esperar. Es en memoria y por proceso; detrás de Render toma la IP real con `TRUST_PROXY_HEADERS=true`.
- **Consentimiento.** Cada pregunta de la encuesta explica que las respuestas se usan de forma agregada y anónima, y que sólo se publican con 5 o más negocios. La grabadora avisa que el audio se borra a los 7 días.

Tests: `backend/tests/test_demo_hardening.py`, más e2e en `auth.spec.ts` (429) y `onboarding.spec.ts` (avisos). ✅

---

## 6. 🟡 Visibilidad básica de errores

No hace falta una torre de observabilidad para un demo — sí conviene enterarte si se cae mientras lo estás compartiendo.

**Tarea para Claude Code:** agregar tracking de errores básico (Sentry en su capa gratuita, o incluso un canal de logs centralizado simple) en frontend y backend, y un endpoint de salud que revise Snowflake/Nessie/LLM (en modo mock está bien simularlo) y no sólo "el proceso está vivo".

---

## 7. 🟡 Ampliar cobertura de pruebas

La base ya es sólida (151 backend + 34 e2e) — esto no es para "producción", es para poder decir con toda confianza en LinkedIn o en una entrevista técnica que el sistema está probado a fondo, y para que cualquiera que revise el repo no encuentre un hueco.

- Suite de "preguntas doradas" para el asistente (30-50 preguntas con la respuesta/evidencia esperada) corrida en CI, para detectar regresiones de la guardia anti-alucinación.
- Una pasada explícita de checklist de seguridad tipo OWASP para APIs (inyección, límites de tamaño de payload, exposición de stack traces en errores 500).

---

## 8. 🔴 Dejar clarísimo, en todas partes, que no se maneja dinero real

Esto no es una fase técnica compleja, es una lista de verificación de mensaje consistente. El objetivo es que **nadie que vea el proyecto — jueces, reclutadores, gente de Capital One, un usuario curioso — pueda pensar por un segundo que hay dinero real de por medio.**

**Tarea para Claude Code — agregar la misma idea, en el lenguaje que corresponda a cada superficie, en:**
- El disclaimer de la Fase 1 (ya lo cubre, pero verificar que diga explícitamente "todas las transacciones son simuladas; no se procesa dinero real ni se conecta a cuentas bancarias reales").
- La pantalla de bienvenida/landing del frontend, como una línea corta y visible (no escondida en letra pequeña).
- Un indicador visual persistente dentro de la propia app mientras se navega — algo tan simple como una etiqueta "MODO DEMO — datos simulados" en el header o en `BottomNav.tsx`, para que quien esté probando la app nunca pierda de vista que es una simulación.
- El `README.md`, en una frase directa cerca del inicio (no sólo en la sección de disclaimers legales al final).
- Cualquier descripción reutilizada del proyecto (Devpost, el propio post de LinkedIn, la presentación si se vuelve a compartir).

**Criterio de terminado:** una persona que sólo ve una de estas cinco superficies (sin ver las otras cuatro) ya entiende, sin ambigüedad, que es un demo con dinero simulado.

---

## 9. 🟡 Verificación y ajustes finales contra Snowflake real — deliberadamente al final

Todo lo anterior se construyó y se probó sin tocar tu cuenta de Snowflake. Esta es la única fase de todo el roadmap que necesita tus credenciales reales, y por eso va al final: primero se aprueba todo lo demás, y sólo entonces se hace la única sesión que toca la cuenta real.

**Tarea para Claude Code:**
- Con `USE_SNOWFLAKE=true` y tus credenciales reales en `backend/.env`, correr `python -m scripts.migrate` y confirmar que las migraciones (incluida cualquier migración nueva que haya salido de la Fase 5, como mover el audio del onboarding) se aplican sin error.
  - De la Fase 5 salieron dos pasos. Primero, la migración `005_onboarding_audio.sql` (aditiva; también se aplica sola al arrancar). Después, el paso manual `python -m scripts.purge_legacy_profile_audio`: sin `--apply` sólo cuenta cuántos perfiles tienen audio en la fila, y con `--apply` lo vacía.
- Verificar de punta a punta contra la cuenta real: registrar un negocio de prueba, completar el onboarding, hacer una venta por QR y una compra con tarjeta, y confirmar en Snowsight que todo se guardó correctamente (perfiles, usuarios, diario, inventario).
- Revisar la configuración de `AUTO_SUSPEND` y el tamaño del warehouse (`HACKMTY_WH`) en Snowsight, y ajustar el tiempo de auto-suspensión si vas a dejar el demo con un link fijo compartido en LinkedIn (para que la primera visita de alguien no espere varios segundos a que el warehouse "despierte").
- Cerrar el pendiente que quedó anotado en la Fase 3 (`docs/PROJECT_STATUS.md`) sobre si esto ya corrió contra una cuenta real, reemplazándolo por el resultado verificado de esta fase.

**Criterio de terminado:** migraciones aplicadas limpias contra la cuenta real, un flujo completo (registro → onboarding → venta → compra) verificado en Snowsight, warehouse configurado a tu gusto, y `PROJECT_STATUS.md` reflejando el estado real y no uno aspiracional.

---

## 10. Un solo listón: "listo para enseñar y mostrar de lo que somos capaces"

No hay una segunda barra de "listo para usuarios reales" — ese no es el objetivo de este roadmap. El listón único es: **cualquier persona técnica (o de Capital One) que abra el repo, lea el README, o pruebe el demo, entiende en minutos tanto la profundidad del trabajo como los límites que se pusieron a propósito.**

Para llegar ahí hacen falta las Fases 1, 2 ✅, 3, 4, 5, 8 completas, y las Fases 6 y 7 en la medida en que el tiempo lo permita. La **Fase 9 (Snowflake real) sólo es indispensable si el demo que vas a compartir depende de persistencia real en Snowflake** — si te basta con que el demo público corra en modo mock/sqlite (que funciona idéntico, sólo sin guardar entre reinicios), puedes saltarte la Fase 9 sin que eso afecte qué tan "listo para enseñar" se ve el proyecto. Si quieres poder decir honestamente "esto corre sobre Snowflake real" en LinkedIn, entonces sí es parte del listón.

---

## 11. Ideas de extensión para un producto real — evaluadas, no implementadas a propósito

Esto **no es una fase para Claude Code**, es contenido para una sección del propio `README.md` o `docs/PROJECT_STATUS.md` (título sugerido: *"Si esto fuera un producto real: lo que ya pensamos y decidimos no construir en 36 horas"*). El objetivo es señalar madurez de criterio — que quede claro que estas cosas no se les pasaron por alto, sino que las evaluaron y conscientemente las dejaron fuera del alcance de un hackathon:

- **Integraciones bancarias/de pago reales.** Nessie (el sandbox de Capital One) y el proveedor de pagos demo funcionan perfecto para simular el flujo; un producto real necesitaría Plaid/Finicity y Stripe/Square detrás de las mismas interfaces (`NessieClient`, `PaymentProvider`) que ya existen en el código — la abstracción está lista, la integración no, a propósito.
- **OCR real de tickets de compra**, hoy con tickets de muestra; `PurchaseService.attach_receipt` es el punto de entrada ya diseñado para eso.
- **Arquitectura de datos híbrida para escala real** (mover las tablas de alta frecuencia a una base OLTP y dejar Snowflake para lo analítico) — Snowflake es excelente para lo que se usa aquí (autoritativo + Cortex + analítica cross-negocio), pero no está pensado para latencia transaccional baja a gran escala; es una tensión arquitectónica real que se documenta, no se resuelve, en esta etapa.
- **Multi-moneda real** más allá del truco de que dólares y pesos mexicanos comparten símbolo.
- **Cumplimiento regulatorio** (KYC/AML, PCI-DSS, transmisión de dinero) — necesario sólo el día que exista dinero real de terceros moviéndose por la plataforma, que no es el plan actual.

**Tarea para Claude Code:** redactar esta sección con el tono de "decisión de producto consciente", no de "lista de pendientes que no dio tiempo de hacer" — es una diferencia de framing importante para quien lo lea.

---

## 12. Orden sugerido de sesiones con Claude Code

1. Fase 3 (auditoría, en modo mock) — sesión corta, diagnóstico puro.
2. Fase 1 + Fase 8 (transparencia de marca, mensaje de "no es dinero real") — buena combinación, todo es documentación/frontend ligero. (Fase 2 ya está hecha.)
3. Fase 4 (Cash Insight) — sesión dedicada, toca frontend + backend.
4. Fase 5 (datos/seguridad del demo, en modo mock) — sesión dedicada.
5. Fase 6 y Fase 7 (visibilidad de errores, tests) — pueden ir juntas.
6. Fase 11 (ideas de extensión) — redacción, se puede hacer en cualquier momento, no depende de las demás.
7. **Fase 9 (Snowflake real) — la última, sin excepción.** Sólo cuando todo lo anterior ya te convenció, abres esta sesión con tu `.env` real.

---

## 13. Qué darle a Claude Code además de este documento

**Archivos:**
- Este roadmap, versionado dentro del propio repo como `docs/ROADMAP_PULIDO.md` (así queda con el resto de la documentación del proyecto, no sólo en tu escritorio).
- `docs/ANALISIS_PROFUNDO.md` — ya lo colocaste tú mismo (Fase 2, hecha).
- Nada más hace falta explícitamente: `CLAUDE.md`, `AGENTS.md` y `.claude/skills/` ya existen en el repo y Claude Code los recoge solo al abrir la sesión ahí.

**Para que tú controles cada commit y cada PR (esto es lo importante):**

1. **Bloquéalo a nivel de repo, no sólo de prompt.** Agrega una línea a `CLAUDE.md` (que ya se lee automáticamente en cada sesión) del estilo: *"Este agente nunca ejecuta `git commit`, `git push` ni abre pull requests. Todo cambio se deja sin commitear para revisión humana."* Así no depende de que te acuerdes de repetirlo cada vez — queda como regla del proyecto.
2. **Una rama por fase.** Antes de cada prompt, tú corres `git checkout -b fase/0X-nombre-corto` desde `main` actualizado. Así cada fase es revisable y revertible de forma independiente, y si una fase sale mal no contamina las demás.
3. **Corre Claude Code en modo interactivo, no autónomo.** No uses un modo de "auto-aceptar todos los cambios" para este trabajo — quieres ver y aprobar cada edición de archivo mientras pasa, no sólo el resultado final. Es una capa de revisión adicional a la del PR.
4. **Al terminar la fase, revisa tú el diff completo** (`git status`, `git diff`) antes de decidir qué stagear. Escribe tu propio mensaje de commit (puedes usar el "Criterio de terminado" de cada fase como checklist de qué debería estar cubierto).
5. **Push de la rama + Pull Request hacia `main`, hecho por ti.** Aunque trabajes solo, el PR te da una vista de diff limpia y dispara el CI que ya existe en el repo (`ruff` + `pytest` + build de frontend) automáticamente — es una segunda red de seguridad gratis antes de mergear.
6. **Secrets sólo en la Fase 9.** Todas las demás fases (1, 3, 4, 5, 6, 7, 8, 11) se hacen y se prueban en modo mock/sqlite — no necesitan tu `.env` con credenciales reales de Snowflake ni de Anthropic. La única sesión que sí lo necesita es la Fase 9, al final.
7. **Opcional pero útil:** agrega un `.github/pull_request_template.md` sencillo con checkboxes que reflejen el "criterio de terminado" de las fases — hace que revisar cada PR sea mecánico en vez de tener que releer este documento cada vez.
