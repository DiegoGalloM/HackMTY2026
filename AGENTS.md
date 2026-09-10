# AGENTS.md — contexto para Claude/IA trabajando en este repo

## Qué es esto

Base de repo para el reto de Capital One en HackMTY 2026. Backend en
FastAPI que envuelve la API de Nessie (banca simulada) detrás de una
interfaz común, para poder cambiar entre datos reales y mock sin tocar el
resto del código. Frontend en React/Vite pensado para servirse como web Y
empaquetarse como app de escritorio (Tauri o Electron, ver `desktop/`).

**La idea de producto todavía no está definida** — este repo es la
plomería (auth-less, sin dominio de negocio todavía), no el producto final.

## Estructura

```
backend/app/
  main.py            # FastAPI app + rutas registradas
  config.py          # Settings desde .env (pydantic-settings)
  nessie/
    base.py          # Interfaz común (ABC)
    real_client.py   # Cliente real contra api.nessieisreal.com
    mock_client.py   # Cliente mock en memoria (mismos métodos)
    __init__.py      # get_nessie_client() -> real o mock según .env
  routers/
    accounts.py
    transactions.py
  models/schemas.py  # Pydantic models de respuesta
  services/insights.py  # placeholder para la capa de IA/análisis
frontend/src/
  App.jsx            # dashboard starter, REEMPLAZAR por la idea real
desktop/README.md     # cómo empaquetar frontend/ como app nativa
```

## Regla de oro

Nunca llamar a `httpx` directo desde un router o servicio — siempre a
través de `Depends(get_nessie_client)`. Así, si Nessie se cae durante el
hackathon, cambiar `USE_MOCK_NESSIE=true` en `.env` basta para seguir
developing/demoing sin tocar una sola línea de lógica de negocio.

## Patrones ya establecidos (seguirlos, no reinventarlos)

- **Service result implícito vía HTTPException**: los routers lanzan
  `HTTPException` en errores esperados (404, etc.), no devuelven `None`
  silenciosamente.
- **useCallback antes que el useEffect que lo usa** en el frontend.
- Todo dato sensible (API keys) vive en `.env`, nunca hardcodeado — ver
  `.env.example` para la lista completa de variables.

## Comandos

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

## Cuando el equipo decida la idea final

Lo que probablemente cambia:
- Nuevos routers en `backend/app/routers/` para el dominio específico.
- `services/insights.py` deja de ser un placeholder y llama a
  Gemini/Claude de verdad.
- `frontend/src/App.jsx` se reemplaza por las pantallas reales.

Lo que probablemente NO cambia: `nessie/`, el CI, el patrón de config.
