# Setup de Snowflake — Capital One Business (HackMTY 2026)

Esta guía es para que cualquiera del equipo pueda activar el guardado real
en Snowflake sin tener que preguntarle a Diego paso por paso. Al final,
`USE_SNOWFLAKE=true` en su `.env` local hace que los perfiles de negocio
de la encuesta se guarden en Snowflake real en vez de memoria.

## Paso 1 — Crear la cuenta (si no la tienen ya)

1. Vayan al [trial de estudiante de 120 días](https://mlh.link/snowflake-signup)
   del reto de MLH. Si por algo no aplica, usen el
   [trial estándar de 30 días](https://signup.snowflake.com/) — para el
   hackathon cualquiera de los dos sirve igual.
2. Usen su correo institucional del Tec si pueden.
3. Dejen la nube/región en el default (normalmente AWS US East) a menos
   que ya tengan preferencia.
4. Confirmen el correo y entren a Snowsight (la interfaz web).

## Paso 2 — Sacar su Account Identifier

Esto es lo que más tarda la primera vez que alguien usa Snowflake.

1. En Snowsight: clic en su nombre de usuario (esquina inferior
   izquierda) → **Account** → **View account details**.
2. Copien el valor de **Account Identifier**. Se ve como
   `abcd123-xy98765` (formato organización-cuenta) o `xy12345` (formato
   legado, más corto).
3. Alternativa más rápida — péguenlo directo en un worksheet nuevo de
   Snowsight y corran:

   ```sql
   SELECT CURRENT_ORGANIZATION_NAME() || '-' || CURRENT_ACCOUNT_NAME() AS "Account Identifier";
   ```

⚠️ El identificador **no** lleva `.snowflakecomputing.com` al final — solo
la parte antes de eso.

## Paso 3 — Crear warehouse, base de datos y la tabla

En un worksheet nuevo de Snowsight, corran esto completo y en orden (ya
está diseñado para este proyecto, no hace falta cambiar nada):

```sql
CREATE WAREHOUSE IF NOT EXISTS HACKMTY_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS HACKMTY;
CREATE SCHEMA IF NOT EXISTS HACKMTY.PUBLIC;

USE WAREHOUSE HACKMTY_WH;
USE DATABASE HACKMTY;
USE SCHEMA PUBLIC;

CREATE TABLE IF NOT EXISTS business_profiles (
  owner_id STRING PRIMARY KEY,
  category STRING,
  operating_days ARRAY,
  city STRING,
  employees STRING,
  answers VARIANT,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

Verifiquen que quedó creada:

```sql
SELECT * FROM business_profiles;
```

Debe salir vacía (0 filas) — eso significa que sí existe.

## Paso 4 — Anotar sus credenciales

Si la cuenta con la que se registraron tiene el rol `ACCOUNTADMIN`,
pueden usarla directo para el hackathon (no es buena práctica a largo
plazo, pero para 36 horas está bien). Anoten en un lugar seguro (no en el
canal general del equipo):

- Usuario (el que usan para entrar a Snowsight)
- Password
- Rol por default (normalmente `ACCOUNTADMIN` o `SYSADMIN`)

## Paso 5 — Llenar el `.env` del backend

En su copia local del repo, dentro de `backend/.env` (cópienlo de
`.env.example` si no lo tienen), llenen:

```
USE_SNOWFLAKE=true
SNOWFLAKE_ACCOUNT=abcd123-xy98765        # el del Paso 2
SNOWFLAKE_USER=su_usuario
SNOWFLAKE_PASSWORD=su_password
SNOWFLAKE_WAREHOUSE=HACKMTY_WH
SNOWFLAKE_DATABASE=HACKMTY
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

⚠️ **Este `.env` nunca se sube a git** — ya está en `.gitignore`. Tampoco
lo peguen en el chat general del equipo; si necesitan compartir
credenciales entre ustedes, mándenlas por mensaje directo.

## Paso 6 — Instalar la dependencia nueva y probar

```bash
cd backend
source .venv/bin/activate   # o como tengan armado su entorno
pip install -r requirements.txt   # ya incluye snowflake-connector-python
uvicorn app.main:app --reload
```

En otra terminal:

```bash
curl -X POST http://localhost:8000/business-profile/prueba1 \
  -H "Content-Type: application/json" \
  -d '{"category":"comida","operating_days":["mon","tue"],"city":"Monterrey","employees":"1","answers":{"se_ha_quedado_sin_stock":true}}'

curl http://localhost:8000/business-profile/prueba1
curl http://localhost:8000/business-profile/stats/comida
```

Si el segundo y tercer comando regresan datos (no un error), ya está
guardando en Snowflake real. Confírmenlo también directo en Snowsight:

```sql
SELECT * FROM business_profiles WHERE owner_id = 'prueba1';
```

## Si algo falla

| Error / síntoma | Causa probable | Qué hacer |
|---|---|---|
| `250001: Could not connect to Snowflake backend` | Account identifier mal escrito | Revisen que no tenga `.snowflakecomputing.com` al final |
| `Warehouse 'HACKMTY_WH' does not exist or not authorized` | No corrieron el `USE WAREHOUSE` del Paso 3, o el rol no tiene acceso | Vuelvan a correr el Paso 3 completo, en orden |
| El GET regresa `null` pero el POST dijo `"status":"ok"` | El JSON de `answers` no se guardó bien | En Snowsight: `SELECT answers FROM business_profiles WHERE owner_id='prueba1';` |
| La primera llamada tarda varios segundos | Normal — el warehouse estaba "dormido" (`AUTO_SUSPEND`) y despierta solo | Las siguientes llamadas ya son rápidas |
| Cualquier otro error de conexión | — | Péguenle el mensaje de error completo a Claude Code o Codex, con este archivo de contexto |

## Si de plano no da tiempo

No bloquea nada más del proyecto: dejen `USE_SNOWFLAKE=false` y el resto
de la app sigue funcionando exactamente igual con datos en memoria — se
pierde la elegibilidad para el prize de "Best Use of Snowflake", pero el
producto principal (Capital One) sigue de pie completo.
