# Deploy — backend y frontend siempre prendidos

El objetivo: una sola URL publica del backend y una del frontend, para que
cualquiera del equipo (y los jueces, y un celular) entre sin correr nada
localmente. El archivo `render.yaml` en la raiz ya describe los dos servicios.

Render es la opcion recomendada porque el plan gratis no pide tarjeta y lee
`render.yaml` directo del repo. Cualquier host que corra Python sirve igual.

## Paso 1 — Subir la rama a GitHub

Render despliega desde GitHub, asi que lo que no este pusheado no existe:

```bash
git push -u origin <su-rama>
```

Pueden desplegar desde una rama; no tiene que ser `main`.

## Paso 2 — Crear el blueprint

1. Cuenta en [render.com](https://render.com) (el plan free basta) y conecten
   su GitHub.
2. **New → Blueprint** → elijan este repo → Render detecta `render.yaml` y
   propone dos servicios: `hackmty2026-api` y `hackmty2026-web`.
3. Si los nombres ya estan tomados por alguien mas en Render, les va a poner un
   sufijo. Anoten los nombres reales, se ocupan en el Paso 4.

## Paso 3 — Capturar las variables secretas

Las variables marcadas `sync: false` en `render.yaml` **no** viven en el repo —
Render las pide al crear el blueprint. En `hackmty2026-api` llenen:

| Variable | Valor |
|---|---|
| `SNOWFLAKE_ACCOUNT` | su Account Identifier (Paso 2 de `SNOWFLAKE_SETUP.md`) |
| `SNOWFLAKE_USER` | su usuario de Snowsight |
| `SNOWFLAKE_PASSWORD` | su password |
| `NESSIE_API_KEY` | su key de Nessie (o dejenla vacia y `USE_MOCK_NESSIE=true`) |
| `CORS_ORIGINS` | pendiente hasta el Paso 4 — pongan `http://localhost:5173` por ahora |

⚠️ Estas credenciales van **solo** en el dashboard de Render, nunca en
`render.yaml` ni en ningun archivo del repo.

El warehouse, database, schema y rol ya vienen con valor en `render.yaml`
(`HACKMTY_WH` / `HACKMTY` / `PUBLIC` / `ACCOUNTADMIN`). Cambienlos ahi si su
cuenta usa otros.

## Paso 4 — Amarrar las dos URLs

Cada servicio necesita la URL del otro, asi que esto se hace despues del primer
deploy, cuando Render ya asigno los dominios:

1. Copien la URL del backend, algo como `https://hackmty2026-api.onrender.com`.
2. En `hackmty2026-web` → Environment → `VITE_API_URL` = esa URL.
   Vite hornea la variable en el build, asi que hay que **Manual Deploy** del
   frontend para que agarre.
3. Copien la URL del frontend, `https://hackmty2026-web.onrender.com`.
4. En `hackmty2026-api` → Environment → `CORS_ORIGINS` = esa URL.
   **Sin diagonal final** — `https://algo.onrender.com/` con `/` al final no
   hace match y el navegador bloquea todas las llamadas.
   Pueden poner varias separadas por coma si quieren seguir usando localhost:
   `https://hackmty2026-web.onrender.com,http://localhost:5173`

## Paso 5 — Probar

```bash
curl https://hackmty2026-api.onrender.com/health
```

Debe responder `{"status":"ok","nessie_mode":"mock"}`. Luego abran la URL del
frontend, completen el onboarding, y confirmen en Snowsight:

```sql
SELECT * FROM business_profiles ORDER BY created_at DESC LIMIT 5;
```

## Lo que hay que saber del plan gratis

- **El servicio se duerme** a los ~15 minutos sin trafico. La primera llamada
  despues tarda ~50 segundos en responder mientras el contenedor arranca.
  Antes de presentar, peguenle a `/health` un par de minutos antes para
  despertarlo. Es el detalle que mas feo se ve en una demo en vivo.
- Sumado a eso, el warehouse de Snowflake tambien se suspende
  (`AUTO_SUSPEND = 60`). Frio + frio pueden ser ~60 segundos la primera vez.
- 750 horas gratis al mes por cuenta, de sobra para el hackathon.

## Si prefieren no desplegar

Sin deploy, cada quien corre backend y frontend en su propia maquina y todo
funciona igual: `VITE_API_URL` no definida = `http://localhost:8000`. Lo unico
que no se puede es abrir la app desde un celular o mandarle un link a alguien.
