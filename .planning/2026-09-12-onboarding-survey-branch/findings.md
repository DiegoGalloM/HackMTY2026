# Findings — Onboarding Survey Branch

## Auditoría inicial (2026-09-12)

### Bugs de conexión encontrados (bloquean build/dev)

1. **`backend/app/main.py` NO incluye el router `business_profile`.**
   El usuario dijo haberlo agregado pero no está: solo importa/incluye
   `accounts` y `transactions`. Sin esto, `POST/GET /business-profile/{owner_id}`
   da 404. Fix: importar `business_profile` desde `app.routers` e
   `app.include_router(business_profile.router)`.

2. **Nombre de archivo real: `frontend/src/onboarding/Logo,jsx`** (coma en vez
   de punto). El contenido del archivo es correcto y ya trae el comentario
   de que el logo es un placeholder pendiente (texto "Capital One Business"
   en vez de imagen) — coincide con lo que pidió el usuario, NO hay que
   inventar un logo, solo renombrar el archivo a `Logo.jsx`.

3. **Casing real de archivos no coincide con lo que el usuario reportó:**
   - Reportado `PhoneFrame.jsx` → real `phoneFrame.jsx` (p minúscula)
   - Reportado `Onboarding.jsx` → real `onBoarding.jsx` (o minúscula, B mayúscula)
   - `App.jsx` importa `./onboarding/phoneFrame.jsx` y `./onboarding/onBoarding.jsx`
     y `./onboarding/Logo.jsx` — los dos primeros SÍ coinciden con los nombres
     reales en disco; el tercero (Logo.jsx) NO coincide porque el archivo real
     tiene la coma.
   - Windows es case-insensitive por defecto, así que esto compila y corre
     localmente sin quejarse, pero es frágil: en un filesystem case-sensitive
     (Linux CI, Vercel, Netlify, GitHub Actions ubuntu-latest) los imports con
     casing distinto AL REAL fallarían. Como los nombres de phoneFrame/onBoarding
     ya coinciden entre archivo e import, no son bug funcional hoy, pero vale
     la pena unificar a PascalCase (convención de componentes React) para
     evitar sorpresas futuras y por legibilidad.

### Ya existe un logo subido (no hay que generarlo, pero tampoco usarlo aún)
`frontend/public/logo-capital-one-business.jpeg` ya está en el repo. El
comentario en `Logo,jsx` dice que en cuanto tengan el logo lo reemplacen por
un `<img src="/logo-capital-one-business.jpeg" .../>`. El usuario pidió
explícitamente NO inventar/generar un logo — dejamos el placeholder de texto
tal cual y solo dejamos anotado en el plan que el archivo de imagen ya está
subido por si el usuario decide activarlo él mismo más adelante (no lo
activamos sin que él lo pida).

### Estructura backend confirmada
- `app/routers/__init__.py` existe junto con `accounts.py`, `transactions.py`,
  `business_profile.py` — estructura de router está bien, solo falta el include.
- Tests existentes en `backend/tests/test_health.py` cubren `/health`,
  `/accounts/...`, `/accounts/.../transactions` — no hay tests para
  `business_profile` todavía (el usuario no pidió agregarlos, no se agregan
  salvo que se pida).

### Frontend — flujo de Onboarding.jsx (real: onBoarding.jsx)
Steps: `welcome → questions → schedule → employees → city → done`.
- `submit()` hace POST a `${API_BASE}/business-profile/${ownerId}` con
  `API_BASE = "http://localhost:8000"` hardcodeado (aceptable para hackathon/demo).
- `detectCity()` llama a `nominatim.openstreetmap.org` (servicio externo real,
  no es problema de seguridad para un hackathon pero anotar que depende de
  red/CORS del navegador, no del backend).
- No hay transiciones/animación entre steps todavía — theme.css no define
  ninguna transición de entrada/salida de pantalla. Ese es el trabajo de la
  fase de ui-ux-pro-max (fade/slide entre preguntas).

### Bug encontrado en prueba end-to-end (Fase 3)
`submit()` en `Onboarding.jsx` (real: era `onBoarding.jsx`) hacía el POST
correctamente pero **nunca avanzaba `step` a `"done"`** — no había ningún
`goToStep("done")`. Resultado: el usuario terminaba de llenar todo, el
backend SÍ guardaba el perfil (confirmado con GET), pero la pantalla se
quedaba congelada en el paso "city" sin mostrar "¡Listo! 🎉" ni el mensaje
de error. Encontrado corriendo el flujo real con Playwright headless (no se
hubiera visto solo con `pytest`/`npm run build`, que no ejecutan la lógica
de UI). Fix aplicado: envolver el fetch en try/catch/finally y llamar
`goToStep("done")` siempre en el finally, para que muestre éxito o el
mensaje de "Algo salió mal" según corresponda.

### theme.css — paleta confirmada
`--c1-red: #d03027` (el usuario dijo #D03027, coincide) y
`--c1-navy: #004977` (coincide). Bubbles ya usan variant yes/no con navy/rojo.
