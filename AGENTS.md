# AGENTS.md — context for Claude/AI working on this repo

## What is this

Base repo for the Capital One challenge at HackMTY 2026. FastAPI backend that wraps the Nessie API (simulated banking) behind a common interface, so we can switch between real and mock data without touching the rest of the code. React/Vite frontend designed to be served as a web app AND packaged as a desktop app (Tauri or Electron, see `desktop/`).

**The product is Capital One Business**: SMB cash-flow and working-capital
intelligence for nano/micro-businesses. The owner sells with a QR and pays with
the business card; the app keeps inventory, double-entry books, statements,
ratios and a natural-language assistant underneath. Read
`docs/FINANCIAL_CORE.md` (architecture + invariants) and `docs/DEMO.md` (judge
script) before touching the financial core.

## Structure

```
backend/app/
  main.py            # FastAPI app + registered routes
  config.py          # Settings from .env (pydantic-settings)
  nessie/
    base.py          # Common interface (ABC)
    real_client.py   # Real client against api.nessieisreal.com
    mock_client.py   # In-memory mock client (same methods)
    __init__.py      # get_nessie_client() -> real or mock based on .env
  db/                # Database abstraction: sqlite (local/tests) | Snowflake (pooled)
  finance/           # accounting, inventory, catalog, sales, payments, purchases,
                     # analytics, assistant, knowledge, llm, demo seed (see docs/FINANCIAL_CORE.md)
  routers/
    accounts.py, transactions.py   # Nessie passthrough (legacy)
    auth.py, business_profile.py   # session + onboarding profile
    finance.py         # /business/{owner_id}/... owner-scoped financial API
    checkout.py        # /pay/{token} public customer checkout (QR)
    health.py          # /health (liveness for Render) and /health/ready (db, Nessie, LLM)
  observability.py     # optional Sentry (SENTRY_DSN), event scrubbing, 500 handler with error_id
  ratelimit.py         # per-IP limits on public routes
    demo.py            # /demo/session + /business/{owner_id}/demo/seed
  models/schemas.py, models/finance.py  # Pydantic contracts
sql/003_financial_core.sql, 004_financial_views.sql  # portable migrations (sqlite + Snowflake)
frontend/src/            # Vite + React + TS + Tailwind v4, mobile-first PWA
  App.tsx                # rutas (HashRouter) + AnimatePresence + BottomNav
  components/            # BalanceHeader, CreditCardTile, QuickActionsGrid,
                         # BottomNav, Screen (wrapper de transición + padding)
  screens/               # Cuenta, Vender (QR), CobroEfectivo, Inventario, Compras, Libros,
                         # Asistente (/analisis: chat + opening brief), Resumen, Educacion,
                         # Pay (public checkout, /#/pay/:token), Retiros, Transferencias, Pagos, Mas
  onboarding/, auth/     # landing → welcome, register/login forms and the onboarding survey
  financial-literacy/    # survey-driven Cash Insight triggers (insights.js) + micro-lessons
  api/                   # config (API_BASE), client, types (API contracts), finance (typed endpoints), format (USD)
  business/              # BusinessContext (session + api + refresh) and useBusinessQuery
  data/mock.ts           # demo data for the legacy banking screens only
desktop/README.md     # how to package frontend/ as a native app

```

## Golden rule

Never call `httpx` directly from a router or service — always go through `Depends(get_nessie_client)`. This way, if Nessie goes down during the hackathon, changing `USE_MOCK_NESSIE=true` in `.env` is enough to keep developing/demoing without touching a single line of business logic.

## Established patterns (follow them, don't reinvent them)

* **Implicit service result via HTTPException**: routers raise `HTTPException` on expected errors (404, etc.), they don't silently return `None`.
* **useCallback before the useEffect that uses it** in the frontend.
* All sensitive data (API keys) lives in `.env`, never hardcoded — see `.env.example` for the complete list of variables.

## Commands

```bash
# Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest -q

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
npm run build

```

## Financial core rules

* Numbers come from the backend (journal → derived views → analytics). Never
  compute a financial figure in React, and never let the LLM produce one.
* Every domain query goes through `Repo` (bound to one `business_id`);
  routers under `/business/{owner_id}` are guarded by `require_owner`.
* New tables = new numbered migration in `backend/sql/` in the portable SQL
  subset (runs on sqlite and Snowflake). Tests never touch Snowflake.
* Only a `PaymentEvent` with status SUCCEEDED changes books/inventory.

## Legacy pieces still in the repo

The final idea is built (see above). A few pieces from the pre-hackathon
template remain on purpose and are not the product path:

* `services/insights.py` is an unused placeholder; the real intelligence lives
  in `backend/app/finance/` (analytics + assistant, LLM via `finance/llm.py`).
  `GEMINI_API_KEY` is read by config but nothing uses it.
* `frontend/src/data/mock.ts` still feeds the legacy banking screens (Retiros,
  Pagos, CobroEfectivo sheets…) and the no-session fallback in Cuenta; financial
  screens call FastAPI through `api/finance.ts`.
* `routers/accounts.py` / `transactions.py` are the Nessie passthrough.

Current project state and pending checks: `docs/PROJECT_STATUS.md`.