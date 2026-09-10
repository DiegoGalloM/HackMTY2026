# HackMTY 2026 — Reto Capital One

Base de repo genérica para el reto de Capital One en HackMTY 2026 ("herramientas
financieras más inteligentes con datos en tiempo real"). Pensada para poder
arrancar código el día del evento sin perder tiempo en setup, incluso sin tener
la idea final 100% cerrada.

## ⚠️ Contexto (léelo antes de asumir nada)

Al momento de crear este repo, HackMTY 2026 **no había publicado aún** la
rúbrica ni los requisitos exactos del reto. Todo lo de abajo está basado en el
patrón de **HackMTY 2025** (mismo organizador, TEC ACM, y Capital One como
sponsor recurrente), así que tómalo como la apuesta más probable, no como
hecho confirmado. Verifica esto en cuanto abran el Devpost / kickoff del
viernes.

### Lo que se repitió en HackMTY 2025

- **API de Capital One: "Nessie"** (`api.nessieisreal.com`) — API mock de
  banca: cuentas, clientes, transacciones peer-to-peer, depósitos, retiros,
  pago de bills, cajeros y sucursales. No es streaming real, pero se puede
  *simular* tiempo real haciendo polling o generando transacciones sintéticas
  con un script que las va insertando.
- **Criterio del track de Capital One**: "Tackle real-world financial
  problems by building a unique and technical solution. Use Capital One's
  'Nessie' API to power your hack, simulating transactions, transfers, and
  purchases."
- **Entregables de Devpost**: prototipo funcional hosteado (repo propio,
  Heroku, etc.), descripción del problema/solución/tech stack, link al repo,
  pitch de impacto, **video demo de máximo 2 minutos**, y opcionalmente
  diagramas/wireframes.
- **Equipos de 4 integrantes.**
- **Riesgo real y documentado**: en 2025 la API de Nessie se cayó a media
  competencia y no volvió — un equipo tuvo que cambiar de backend a medio
  hackathon. Por eso este repo trae desde el día 1 un cliente "mock" con la
  misma interfaz que el cliente real (ver `backend/app/nessie/`), para poder
  cambiar de uno a otro con una sola variable de entorno si Nessie se cae.

## Arquitectura

```
┌─────────────┐      HTTP/WS      ┌──────────────┐      HTTP      ┌─────────────┐
│  Frontend   │ ────────────────► │   Backend    │ ─────────────► │   Nessie    │
│ (React/Vite)│ ◄──────────────── │  (FastAPI)   │ ◄───────────── │  API / mock │
└─────────────┘                   └──────────────┘                └─────────────┘
      │
      ├── Se sirve como web dashboard normal (Vite build)
      └── El MISMO build se empaqueta como app de escritorio con Tauri
          (ver desktop/README.md) → así NO es "solo una página web" sin
          duplicar el frontend.
```

Decisión de diseño: en vez de escribir un frontend para web y otro para
escritorio, se recomienda **Tauri** — toma el mismo build de React/Vite y lo
empaqueta como binario nativo (Windows/Mac/Linux), mucho más ligero que
Electron. Si el equipo no ha usado Rust/Tauri antes, **pruébenlo esta noche,
no durante el hackathon** — instalar el toolchain de Rust a medio evento es
un riesgo de tiempo innecesario. Plan B si Tauri da problemas: Electron
(más pesado pero más conocido) — la carpeta `desktop/` trae instrucciones
para ambos casos.

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

Docs interactivos en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests + CI

```bash
cd backend
pytest
```

El pipeline de GitHub Actions (`.github/workflows/ci.yml`) corre lint + tests
en cada PR — configúralo desde el primer commit, no al final (ver Fase 7 del
framework: "no tener CI/CD" es uno de los errores más comunes).

## Siguiente paso

Este repo es intencionalmente genérico — el dominio real (qué hace el
producto) todavía no está definido. Una vez que el equipo elija la idea,
lo que cambia es principalmente `backend/app/routers/`,
`backend/app/services/insights.py` y las pantallas del frontend; el cliente
de Nessie, el CI y el empaquetado de escritorio se quedan igual.
