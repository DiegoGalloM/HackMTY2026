# Plan: Rama Encuesta-inicial (onboarding survey) — HackMTY 2026

## Goal
Dejar funcionando de punta a punta el flujo de onboarding (bienvenida →
categoría → preguntas → días → empleados → ciudad → submit) conectado al
backend FastAPI, sin romper la paleta/estilo de burbujas, y luego pulir la
transición entre preguntas con ui-ux-pro-max. NO generar/inventar un logo.

## Ya está hecho (según el usuario, confirmado por lectura de código)
- `frontend/src/onboarding/PhoneFrame.jsx` (real: `phoneFrame.jsx`)
- `frontend/src/onboarding/Bubble.jsx`
- `frontend/src/onboarding/Logo.jsx` (real: `Logo,jsx` — nombre de archivo con typo)
- `frontend/src/onboarding/questions.js`
- `frontend/src/onboarding/Onboarding.jsx` (real: `onBoarding.jsx`)
- `frontend/src/theme.css`
- `frontend/src/App.jsx` (reemplazado)
- `frontend/src/main.jsx` (import de theme.css agregado)
- `backend/app/routers/business_profile.py`
- `backend/app/models/schemas.py` (BusinessProfile agregado)
- `backend/app/main.py` — el usuario dijo que agregó el router nuevo, pero
  **NO está incluido** (ver Fase 1)

## Falta (lo que hace este plan)
1. Arreglar conexión backend↔router (main.py no incluye business_profile)
2. Arreglar nombre de archivo `Logo,jsx` → `Logo.jsx`
3. Unificar casing de phoneFrame.jsx/onBoarding.jsx a PascalCase (opcional,
   cosmético, confirmar con usuario si quiere o lo dejamos)
4. Verificar build frontend + pytest backend
5. Levantar ambos servidores y probar el flujo completo manualmente
6. ui-ux-pro-max: transición fade/slide entre preguntas
7. Dejar pendiente explícito: logo real (no generar uno)

## Fases

### Fase 1 — Conectar imports/router (backend + frontend)
**Status:** complete
- [x] Agregar `business_profile` al include_router de `backend/app/main.py`
- [x] Renombrar `Logo,jsx` → `Logo.jsx`
- [x] Confirmar que App.jsx importa con el casing correcto tras el rename
- [x] Unificar casing: PhoneFrame.jsx y Onboarding.jsx (usuario confirmó sí renombrar)

### Fase 2 — Build & tests
**Status:** complete
- [x] `pytest -q` en backend/ (4 passed; hubo que crear venv, no existía)
- [x] `npm run build` en frontend/ (build OK, 37 módulos)

### Fase 3 — Prueba manual end-to-end
**Status:** complete
- [x] `uvicorn app.main:app --port 8000` en backend/ (venv creado, corriendo en background)
- [x] Frontend ya corría en `npm run dev` (puerto 5173, del usuario) — verificado que sirve los archivos ya corregidos
- [x] Probado flujo completo con Playwright headless: bienvenida → categoría → preguntas → días → empleados → ciudad → submit
- [x] Confirmado POST a /business-profile/{owner_id} responde 200 y GET lo devuelve con los datos correctos
- [x] **BUG ENCONTRADO Y CORREGIDO**: `submit()` en Onboarding.jsx nunca llamaba `goToStep("done")`, así que la pantalla de éxito era inalcanzable aunque el guardado funcionara. Se agregó `catch` + `goToStep("done")` en el `finally`. Ver findings.md.
- [x] Playwright se instaló temporalmente para la prueba y se desinstaló después (no queda como dependencia permanente)

### Fase 4 — ui-ux-pro-max: transición entre preguntas
**Status:** complete
- [x] Skill `ui-ux-pro-max` no venía instalada en este entorno; el usuario
      instaló el CLI global `ui-ux-pro-max-cli` (`uipro`) y pidió usarlo.
      Se corrió `uipro init --ai claude`, que instaló `.claude/skills/ui-ux-pro-max/`
      en el proyecto (requiere reinicio de sesión para aparecer en el listado
      de skills, así que se leyó `SKILL.md` y se consultó su dataset via
      `python .claude/skills/ui-ux-pro-max/scripts/search.py ... --domain ux`
      directamente en esta misma sesión).
- [x] Agregado fade/slide suave: remount por `key` de React (`transitionKey`
      en `Screen`) + `@keyframes ob-screen-in` en theme.css (opacity 0→1,
      translateX(18px)→0, .32s cubic-bezier ease-out). Respeta
      `prefers-reduced-motion`, usa solo transform/opacity (sin layout shift),
      un solo timing/easing compartido entre todas las pantallas.
- [x] Verificado visualmente con Playwright (captura a mitad de animación
      confirma el fade+slide) y flujo completo sigue llegando a "¡Listo! 🎉"

### Fase 5 — Cierre
**Status:** complete
- [x] Logo: el usuario confirmó que `frontend/public/logo-capital-one-business.jpeg`
      SÍ es el logo real oficial (no un placeholder de prueba). Se conectó en
      `Logo.jsx` (`<img>` en vez del texto), se limpió el CSS muerto
      `.c1b-logo-text*` en theme.css, y se verificó visualmente con Playwright.
- [x] Resumen final al usuario

## Decisiones Made
| Decisión | Razón |
|----------|-------|
| No generar logo | Instrucción explícita del usuario — placeholder de texto se queda |
| Renombrar Logo,jsx → Logo.jsx | Typo de archivo, bloquea el import literal `./Logo.jsx` |
| Agregar include_router business_profile en main.py | Sin esto el endpoint no existe, 404 garantizado |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

## Next Step
Todas las fases completas. Rama lista para revisión/commit por el usuario
(no se hizo commit — el usuario no lo pidió). Pendiente explícito: logo real.
