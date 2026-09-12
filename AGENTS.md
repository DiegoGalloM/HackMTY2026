# AGENTS.md — context for Claude/AI working on this repo

## What is this

Base repo for the Capital One challenge at HackMTY 2026. FastAPI backend that wraps the Nessie API (simulated banking) behind a common interface, so we can switch between real and mock data without touching the rest of the code. React/Vite frontend designed to be served as a web app AND packaged as a desktop app (Tauri or Electron, see `desktop/`).

**The product idea is not yet defined** — this repo is the plumbing (auth-less, without a business domain yet), not the final product.

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
  routers/
    accounts.py
    transactions.py
  models/schemas.py  # Pydantic response models
  services/insights.py  # placeholder for the AI/analytics layer
frontend/src/
  App.jsx            # starter dashboard, REPLACE with the real idea
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

## When the team decides on the final idea

What will probably change:

* New routers in `backend/app/routers/` for the specific domain.
* `services/insights.py` stops being a placeholder and actually calls Gemini/Claude.
* `frontend/src/App.jsx` is replaced by the real screens.

What will probably NOT change: `nessie/`, the CI, the config pattern.