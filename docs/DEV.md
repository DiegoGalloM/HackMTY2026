# DEV — backend y frontend en una sola terminal

Para el día a día. El setup inicial (crear el venv, `npm install`, llenar el
`.env`) está en [CONTRIB.md](./CONTRIB.md); cuando algo se rompe en vivo,
[RUNBOOK.md](./RUNBOOK.md).

## Lo único que hay que recordar

```bash
python dev.py
```

Desde la raíz del repo. Levanta los dos servicios, mezcla su salida en la misma
terminal con prefijo `[api]` / `[web]`, y **un solo Ctrl+C baja los dos**.

```
[dev] api: ...\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload  (cwd=backend)
[dev] web: npm.cmd run dev -- --port 5173 --strictPort  (cwd=frontend)
[dev] listo — Ctrl+C baja los dos
[dev] api  http://127.0.0.1:8000/docs
[dev] web  http://localhost:5173
[api] INFO:     Uvicorn running on http://127.0.0.1:8000
[web]   ➜  Local:   http://localhost:5173/
```

Si uno de los dos se cae, el otro se baja también. Eso es a propósito: quedarse
con medio stack corriendo sin notarlo cuesta más tiempo que volver a arrancar.

## Banderas

| Bandera | Para qué |
|---|---|
| `--only api` / `--only web` | Correr nada más uno de los dos |
| `--api-port 8001` | Mover uvicorn (si el 8000 está ocupado) |
| `--web-port 5174` | Mover vite — **ojo con CORS**, ver abajo |
| `--host 0.0.0.0` | Exponer el backend en la red local (probar desde el celular) |
| `--no-reload` | Apagar el autoreload de uvicorn |

`python dev.py --help` los lista todos.

## Qué hace por ti que las dos terminales no hacían

- **Corre uvicorn desde `backend/`.** `config.py` lee `env_file=".env"` relativo
  al directorio actual, así que desde la raíz no encuentra las credenciales y se
  va a memoria **en silencio** — el error más repetido del RUNBOOK.
- **Le pasa `VITE_API_URL` al frontend** apuntando al backend que acaba de
  levantar. Si tienes un `frontend/.env.local` con otra URL, `dev.py` la pisa
  mientras dure la sesión. Para pegarle a un backend desplegado, usa
  `--only web`.
- **Mata el árbol completo al salir.** En Windows, matar `npm` deja a `node`
  vivo agarrado al puerto, y el siguiente arranque truena con "port in use".
  `dev.py` usa `taskkill /T` para llevarse a los hijos.
- **`--strictPort` en vite.** Sin eso, si el 5173 está ocupado vite se brinca al
  5174 sin avisar y el backend te bloquea por CORS. Mejor que falle de frente.

## Primera vez (o cuando no arranca)

`dev.py` no instala nada — verifica y te dice qué falta. Los dos comandos de
setup:

```powershell
# Backend — Python 3.12 como CI (3.13 también funciona; 3.14 no trae wheels para los pins)
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt

# Frontend
cd frontend
npm install
```

En macOS/Linux es lo mismo con `python3.12 -m venv backend/.venv` y
`backend/.venv/bin/pip`.

### ⚠️ Si el venv existe pero `dev.py` dice que no puede importar uvicorn

Casi siempre es un venv que quedó apuntando a otro intérprete: tiene las
dependencias instaladas para una versión de Python, pero su `pyvenv.cfg` apunta
a otra (por ejemplo al Python de MSYS2/Git Bash). Ese intérprete busca sus
paquetes en otra carpeta y no ve los que ya están, así que `import uvicorn`
falla.

Pasa cuando corres `python -m venv` encima de un venv existente con otro
intérprete: se reescribe el `pyvenv.cfg` y las dependencias viejas quedan
invisibles. `dev.py` lo detecta y te lo dice en vez de tronar con un
`ModuleNotFoundError` suelto.

La reparación es rehacerlo:

```powershell
rmdir /s /q backend\.venv
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
```

`dev.py` también prueba un `.venv` en la raíz del repo y usa el primero que de
verdad pueda importar uvicorn, así que basta con que uno de los dos sirva.

## Si prefieres no usar el script

Ambas alternativas dan una sola terminal, sin tocar el repo:

**Cualquier sistema, sin instalar nada permanente** — `concurrently` vía `npx`:

```bash
npx -y concurrently -n api,web -c cyan,magenta \
  "cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload" \
  "cd frontend && npm run dev"
```

**macOS / Linux / Git Bash** — con `trap` para que Ctrl+C se lleve a los dos:

```bash
trap 'kill 0' EXIT
(cd backend && .venv/bin/python -m uvicorn app.main:app --reload) &
(cd frontend && npm run dev)
```

El `trap 'kill 0'` no es opcional: sin él, Ctrl+C mata el frontend y deja uvicorn
corriendo en el fondo.

## Problemas

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `Encontre venv(s) pero ninguno puede importar uvicorn` | El venv apunta a otro Python, o le faltan deps | El bloque de reparación de arriba |
| `frontend/node_modules no existe` | Nunca se corrió `npm install` | `cd frontend && npm install` |
| `[web] Port 5173 is already in use` | Quedó un `node` huérfano de una sesión anterior | `taskkill /F /IM node.exe` y vuelve a arrancar |
| El navegador bloquea las llamadas al usar `--web-port` | `CORS_ORIGINS` del backend sólo trae `http://localhost:5173` | Agrega el puerto nuevo a `CORS_ORIGINS` en `backend/.env` |
| Cambiaste `.env` y no pasa nada | `get_settings()` está cacheado con `lru_cache`; `--reload` no basta | Ctrl+C y arranca de nuevo |
| Guarda en memoria aunque `USE_SNOWFLAKE=true` | El `.env` está en la raíz y no en `backend/` | Muévelo a `backend/.env` |
| La salida se corta a media línea de vite | Consola en cp1252 sin el fix de encoding | Ya está resuelto en `dev.py`; si lo ves, actualiza tu copia |

Lo demás — Nessie caído, Snowflake, deploy, rollback — está en
[RUNBOOK.md](./RUNBOOK.md).
