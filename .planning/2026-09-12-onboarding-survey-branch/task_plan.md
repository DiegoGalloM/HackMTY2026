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

### Fase 7 — Merge con Pagina-inicio (compañero) + recuperación de trabajo huérfano
**Status:** complete
**Contexto:** el usuario cambió a la rama `Pagina-inicio` (página principal del
compañero: React 19 + Vite 8 + TypeScript + react-router-dom + framer-motion +
Tailwind v4) y corrió `git merge origin/main`. Los únicos conflictos reales
eran `frontend/src/App.jsx` y `frontend/src/main.jsx`, marcados "deleted by
us" (el compañero ya no usaba .jsx, todo su árbol es .tsx).

- [x] Se eliminaron `App.jsx`/`main.jsx` y su lógica se trasladó a
      `App.tsx`/`main.tsx` (únicos entry points válidos, `index.html` ya
      apuntaba a `main.tsx`). `App.tsx` ahora hace de gate: muestra
      `<Onboarding onComplete={...}/>` primero, y al completar renderiza
      `MainApp` (el contenido original del compañero, sin cambios) — ambos
      casos envueltos en `<PhoneFrame>`.
- [x] `frontend/tsconfig.app.json`: agregado `allowJs: true` / `checkJs:
      false` — el build del compañero corre `tsc -b` (type-checked) y sin
      esto rechazaba importar los `.jsx` del onboarding.
- [x] `frontend/src/onboarding/Onboarding.jsx`: se le agregó `onComplete`
      prop + botón "Ir a mi cuenta" en la pantalla final.
- [x] **Hallazgo importante**: el commit `61128f3 "Adición de pregunta y
      grabación de semana de trabajo"` (categoría "Otro" con detalle +
      sección de semana normal con texto/voz) existía en la rama local
      `Encuesta-inicial` pero NUNCA se mergeó a `main` (el PR #2 se hizo
      desde un commit hermano `5a6f2e3` que no lo incluye). No se perdió
      nada, solo quedó huérfano. El usuario pidió traerlo también.
- [x] Como `Onboarding.jsx`/`App.tsx` ya habían cambiado de estructura en
      este merge, se reintegró el contenido de `61128f3` manualmente
      (extraído con `git show 61128f3:<archivo>`) en vez de cherry-pick:
      `Onboarding.jsx` (otro_detail + week_description con MediaRecorder),
      `theme.css` (estilos del recorder + fix `button{appearance:none}` +
      logo margin 36px), `backend/app/models/schemas.py` (campos
      `category_detail`, `week_description_*`).
- [x] `npm run build` (con `tsc -b`) y `pytest -q` verificados en verde.
- [x] Probado end-to-end con Playwright (dispositivo de audio falso):
      Otro+detalle → preguntas → semana narrada por voz (audio real
      grabado y guardado en base64) → días/empleados/ciudad → "Ir a mi
      cuenta" → aparece la pantalla principal del compañero (tarjeta +
      accesos rápidos + movimientos + nav inferior), todo dentro del mismo
      `PhoneFrame`. Sin errores de consola.
- [x] Flujo confirmado con el usuario: por ahora, al terminar la encuesta
      pasa directo a la pantalla de inicio del compañero. Está pendiente
      (explícitamente para después, NO implementar todavía) una pantalla
      intermedia de análisis de resultados de la encuesta entre el final
      del onboarding y la pantalla de inicio.
- [x] Playwright se instaló/desinstaló solo para las pruebas, no queda como
      dependencia permanente. `frontend/package.json` queda sin cambios.

## Decisiones Made
| Decisión | Razón |
|----------|-------|
| No generar logo | Instrucción explícita del usuario — placeholder de texto se queda |
| Renombrar Logo,jsx → Logo.jsx | Typo de archivo, bloquea el import literal `./Logo.jsx` |
| Agregar include_router business_profile en main.py | Sin esto el endpoint no existe, 404 garantizado |
| Eliminar App.jsx/main.jsx a favor de App.tsx/main.tsx | index.html apunta a main.tsx; mantener ambos con "./App" sin extensión es ambiguo para Vite (resuelve a .jsx antes que .tsx) |
| Reintegrar 61128f3 manualmente en vez de cherry-pick | Onboarding.jsx/App.tsx ya cambiaron de forma en el merge; cherry-pick además no es posible con un merge sin commitear |
| No hacer commit del merge todavía | El usuario no lo ha pedido explícitamente en este hilo |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| tsc -b fallaría al importar .jsx desde .tsx sin allowJs | 1 | Agregado allowJs:true / checkJs:false en tsconfig.app.json |
| Puerto 5173/8000 ocupados por procesos de sesiones anteriores | 1 | Identificados con Get-CimInstance/Get-NetTCPConnection y detenidos antes de relanzar |

### Fase 8 — Logo completo de Capital One Business en la tarjeta
**Status:** complete
- [x] El usuario mandó una foto de referencia de una tarjeta Capital One
      Business real y pidió que la tarjeta del compañero (`CreditCardTile.tsx`)
      mostrara el logo completo (con "BUSINESS"), no solo "Capital One".
- [x] `frontend/src/components/CapitalOneLogo.tsx`: se agregó un prop
      `business` opcional que renderiza "BUSINESS" en versalitas espaciadas
      debajo del wordmark, con tamaño relativo (`em`) para heredar el
      font-size del contenedor — mismo patrón vectorial/CSS que ya usaba el
      componente (sin imágenes, así escala y hereda color/tema).
- [x] `CreditCardTile.tsx`: se activó `business` en el uso de
      `<CapitalOneLogo>` de la tarjeta (era el único uso del componente en
      todo el proyecto, así que no afecta nada más).
- [x] Verificado con `npm run build` y una captura de solo la tarjeta —
      coincide con el lockup real ("Capital**One** BUSINESS" arriba, chip,
      nombre, VISA abajo).

### Fase 9 — Reemplazo de la tarjeta CSS por foto real
**Status:** complete
- [x] El usuario proporcionó `frontend/src/assets/capital-one-venture-card.png`
      (foto realista de una tarjeta Capital One Business Venture) y pidió
      reemplazar el diseño dibujado en CSS de `CreditCardTile.tsx` con esta
      imagen tal cual.
- [x] `CreditCardTile.tsx` reescrito: ya no dibuja Swoosh/Chip/BrandMark/
      CapitalOneLogo con CSS — ahora es un `<img>` simple dentro de un
      `motion.div` (mantiene el whileTap de interacción del resto de la app).
- [x] **Bug encontrado en el archivo del usuario**: el PNG no tenía canal
      alpha real (`colorType 2` = RGB sin transparencia) — el cuadriculado
      de "transparencia" que se ve en editores de imagen estaba grabado
      como píxeles reales, no era transparencia de verdad. Se detectó el
      bounding box real de la tarjeta con Python/Pillow (por luminancia) y
      se recortó la imagen a ese cuadro, eliminando el cuadriculado. El
      archivo se sobreescribió en su misma ruta (1536×1024 → 1322×796).
- [x] Se agregó `overflow-hidden rounded-2xl` al contenedor para tapar el
      mínimo triángulo de cuadriculado que quedaba en las 4 esquinas
      (por las esquinas redondeadas reales de la tarjeta vs. el recorte
      rectangular).
- [x] Verificado con `npm run build` y captura del elemento de la tarjeta
      solo: sin rastro de cuadriculado, esquinas limpias.
- [x] `CapitalOneLogo.tsx` con el prop `business` (agregado en la Fase 8)
      quedó sin uso ahora que la tarjeta es una imagen — se dejó intacto
      por si se reutiliza en otra pantalla; no se eliminó.
- [x] Nota de rendimiento: la imagen pesa ~1.27MB tras el recorte (bajó de
      ~1.9MB). Es grande para un PWA con precache — no se comprimió más
      porque no se pidió; mencionado al usuario como posible mejora futura
      (convertir a WebP/comprimir) si el tamaño de descarga importa.

## Next Step
Todo listo y verificado. El merge de `Pagina-inicio` sigue SIN commitear
(git dice "All conflicts fixed but you are still merging") — el usuario
avisó que hará el `git commit` por su cuenta. No se requiere más trabajo de
mi parte salvo que pida algo más antes de eso. Pendiente futuro explícito:
pantalla de análisis de resultados entre encuesta y home (NO implementar
aún, solo mencionado como plan a futuro).
