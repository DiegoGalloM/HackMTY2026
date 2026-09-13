# Capital One Business — Estado del proyecto (HackMTY 2026)

> Escrito para que el equipo pueda retomar sin depender de que Diego esté
> presente. Todo lo de abajo refleja lo que se hizo hasta este momento —
> verifiquen contra el repo real, porque varias piezas las construyó cada
> quien por su lado.

## El proyecto en una línea

**Capital One Business** — reto de Capital One, Track 2 (SMB Cash-Flow &
Working Capital Intelligence). App para micro-empresas (1 a 5 personas) en
Estados Unidos: perfila el negocio con una encuesta de 2 minutos, y desde
ahí ofrece control de flujo de efectivo, inventario y educación financiera
contextual — no cursos genéricos, sino "Cash Insights" que aparecen según
lo que la encuesta o las transacciones revelan del negocio.

Todo está mergeado a `main` en GitHub.

## Cómo correrlo (para ver la demo)

```bash
git clone <url-del-repo>
cd HackMTY2026

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # déjenlo con los defaults, ya funciona sin Snowflake real
uvicorn app.main:app --reload  # http://localhost:8000/docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

Con esto ya deberían poder correr el flujo de onboarding completo en el
navegador (se ve como celular gracias al marco de CSS, no hace falta el
inspector).

## ✅ Terminado y probado

- **Backend (FastAPI)** — corre, tiene tests en verde (`pytest -q` desde
  `backend/`), y CI en GitHub Actions valida lint + tests + build en cada
  push.
- **Integración con Nessie** (API de banca simulada de Capital One) —
  cliente real y un cliente mock intercambiables por variable de entorno
  (`USE_MOCK_NESSIE`), para no depender de que Nessie esté arriba durante
  la demo. Expone cuentas y transacciones.
- **Encuesta de onboarding** — flujo completo: bienvenida → categoría del
  negocio (burbujas) → preguntas sí/no (universales + específicas por
  categoría) → días de operación → número de empleados → ciudad (por
  GPS, con respaldo manual) → guarda el perfil en el backend. Menos de 2
  minutos, cero texto libre salvo la ciudad si el GPS falla.
- **Diseño visual** — paleta de Capital One (rojo `#D03027` / azul marino
  `#004977`), estilo de burbujas tipo chat, marco de teléfono en CSS para
  que se vea como app móvil en cualquier navegador/proyector.
- **Arquitectura de almacenamiento** — interfaz común (`ProfileStore`)
  con implementación en memoria (funciona ahora mismo) y una para
  Snowflake ya escrita (ver pendientes). Cambiar entre las dos es una
  variable de entorno, no requiere tocar código.
- **Contenido de educación financiera** — investigación completa sobre
  FDIC Money Smart for Small Business, SBA Business Smart Toolkit, CFPB,
  Federal Reserve Small Business Credit Survey, Operation HOPE y Accion
  Opportunity Fund. De ahí salieron 11 "triggers" con su microlección ya
  escrita (`frontend/src/financial-literacy/insights.js`): 5 basados en
  respuestas de la encuesta (quiebre de stock, sobrecompra, combinación
  de ambos, guarda inventario, compra al mayoreo) y 6 por categoría de
  negocio (comida, retail, servicios, construcción, transporte, belleza).
  La lógica elige UNA sola tarjeta a mostrar, con prioridad a problemas
  detectados sobre educación genérica.
- **Página principal post-encuesta** — construida por el equipo en
  `frontend/src/screens/Cuenta.tsx`: `BalanceHeader`, `CreditCardTile`,
  `QuickActionsGrid`.

## ⚠️ A medias / en proceso ahorita mismo

- **Conectar la encuesta con la página principal** — el onboarding
  guarda `category` y `answers` pero no los pasa hacia afuera al
  terminar; `Cuenta.tsx` no los recibe todavía como props. Sin esto, la
  tarjeta de Cash Insight no tiene con qué decidir qué mostrar.
- **`CashInsightCard`** — el componente que muestra el trigger elegido
  entre `CreditCardTile` y `QuickActionsGrid`. Bloqueado hasta que el
  punto anterior esté resuelto. Esto se está resolviendo con Codex en la
  rama `feature/financial-literacy` — si alguien la retoma, revisen ahí
  primero antes de reconstruir nada.
- **`snowflake_store.py`** — código completo (interfaz `ProfileStore`,
  MERGE + queries con VARIANT para benchmarks entre negocios), pero
  **nunca se ha probado contra una cuenta real** porque nadie se ha
  registrado todavía. Ver `docs/SNOWFLAKE_SETUP.md` — tiene el paso a
  paso completo, desde crear la cuenta hasta probar que sí guarda datos.

## ✅ Núcleo financiero (2026-09-13)

Implementado y verificado de punta a punta contra Snowflake real (ver
`docs/FINANCIAL_CORE.md` y `docs/DEMO.md`):

- Catálogo de cuentas por giro, diario de partida doble, mayor, balanza
  (ajustada / sin ajustes), estado de resultados y balance general.
- Inventario con costo promedio ponderado, bitácora y conteos; productos y
  servicios con receta; capacidad producible.
- Venta por QR: orden → token opaco → página pública `/pay/:token` → pago
  (proveedor demo, mismo evento que un webhook) → inventario + asientos +
  impuesto apartado, idempotente.
- Compras con la tarjeta: proveedor demo/Nessie normalizado, clasificación
  por reglas + memoria del negocio, revisión en lenguaje llano, tickets que
  actualizan cantidades.
- Análisis: razones explicadas, salud de caja, drivers de utilidad,
  insights de educación basados en datos.
- Asistente híbrido: intención → herramientas sobre el motor → conocimiento →
  redacción (Snowflake Cortex o Anthropic; sin LLM, plantillas). Los números
  nunca salen del LLM.
- Demo: "Panadería La Espiga" con 10 semanas coherentes (`Explorar la demo`).
- Tests: 113 backend (invariantes, flujo HTTP, tenant, asistente) + 25 e2e.

## ❌ No se ha empezado

- **Deploy en Vultr** — para el prize de MLH. No se ha tocado (Render está
  configurado en `render.yaml`).
- **Proveedor de pagos real** — sólo existe el proveedor demo; un Stripe/
  Square entra por la interfaz `PaymentProvider` + webhook.
- **OCR real de tickets** — hay tickets de muestra por comercio; un OCR entra
  por `PurchaseService.attach_receipt`.

## Prioridad sugerida si el tiempo aprieta

1. Terminar el punto de "a medias" (pasar category/answers a Cuenta +
   CashInsightCard) — es lo más cerca de terminarse y es diferenciador
   real frente a otros equipos.
2. Análisis financiero con Nessie — es el corazón del track elegido, sin
   esto el pitch se queda corto en "Technical Depth" e "Impact".
3. Snowflake — alguien crea la cuenta (`docs/SNOWFLAKE_SETUP.md` tiene
   todo el paso a paso) y prueban que `snowflake_store.py` conecta bien.
4. Gemini y Vultr, si alcanza el tiempo — suman prizes de MLH pero no
   son el producto principal.

## Dónde está todo

- Repo: rama `main` tiene todo lo mergeado hasta ahora.
- `docs/SNOWFLAKE_SETUP.md` — guía completa para activar Snowflake real.
- Skills instaladas (globales, sirven en Claude Code/Codex/Antigravity/
  Gemini CLI de quien las haya instalado): `ui-ux-pro-max-skill` (diseño),
  `planning-with-files` (para no perder contexto entre sesiones de
  agentes — actívenla al abrir una sesión nueva en cualquier rama).
