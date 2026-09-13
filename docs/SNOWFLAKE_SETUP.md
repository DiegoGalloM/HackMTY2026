# Setup de Snowflake — Capital One Business (HackMTY 2026)

Esta guía es para que cualquiera del equipo pueda activar el guardado real
en Snowflake sin tener que preguntarle a Diego paso por paso. Al final,
`USE_SNOWFLAKE=true` en su `.env` local hace que los usuarios (registro /
login) y los perfiles de negocio de la encuesta se guarden en Snowflake real
en vez de memoria.

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

## Paso 3 — Crear el esquema con las migraciones

**Ya no hace falta copiar y pegar SQL a mano.** El esquema vive versionado en
`backend/sql/` y se aplica con un runner:

| Archivo | Qué crea |
|---|---|
| `backend/sql/001_business_profiles.sql` | Warehouse `HACKMTY_WH`, base `HACKMTY`, schema `PUBLIC` y la tabla `business_profiles` (encuesta de onboarding) |
| `backend/sql/002_users.sql` | Tabla `users` (registro / login) |
| `backend/sql/003_financial_core.sql` | Las 16 tablas del núcleo financiero (cuentas, diario, inventario, productos, órdenes, pagos, compras, tickets, eventos) |
| `backend/sql/004_financial_views.sql` | Vistas `v_general_ledger` y `v_account_balances` derivadas del diario |

Con `USE_SNOWFLAKE=true` el backend aplica las migraciones pendientes solo al
arrancar (misma lógica y misma tabla `schema_migrations`), así que el runner
manual es opcional. El asistente usa `SNOWFLAKE.CORTEX.COMPLETE` con
`CORTEX_MODEL` (por default `claude-sonnet-4-5`) para redactar; los números
salen del diario, no del modelo.

Corran el runner **desde `backend/`**, después de llenar el `.env` (Paso 5):

```bash
cd backend
python -m scripts.migrate
```

Qué hace:

- lee `backend/sql/*.sql` ordenados por nombre (por eso van numerados),
- anota cada archivo aplicado en una tabla `schema_migrations`,
- se salta los que ya corrieron, así que **correrlo dos veces es seguro**,
- si `USE_SNOWFLAKE=false` o `SNOWFLAKE_ACCOUNT` está vacío, imprime un aviso y
  sale sin conectarse (no es un error: es lo normal si trabajan en memoria).

Cuando agreguen una tabla o columna nueva, **creen un archivo nuevo**
(`003_lo_que_sea.sql`) en vez de editar uno ya aplicado — el runner no vuelve a
correr los que ya están registrados.

⚠️ Las columnas tienen que cubrir **todos** los campos de los modelos de
`backend/app/models/schemas.py` (`BusinessProfile` y `StoredUser`). Si falta
alguna, el POST responde `{"status":"ok"}` pero ese campo se pierde en silencio y
el GET lo regresa como `null` — la grabación de voz de la semana es la que más
duele. Hay tests que lo vigilan (`tests/test_business_profile.py` y
`tests/test_auth.py`): comparan los campos del modelo contra el SQL sin
conectarse a Snowflake.

⚠️ Snowflake acepta `PRIMARY KEY` y `UNIQUE` en el DDL pero **no los impone**:
son metadata para herramientas de modelado. Por eso la unicidad del `username` se
garantiza en el `INSERT ... SELECT ... WHERE NOT EXISTS` de
`SnowflakeUserStore._create_user_sync`, no en la tabla. Si alguna vez migran a
Postgres, ahí sí conviene agregar `UNIQUE(username)`.

Si prefieren verlo en Snowsight, o si el runner no les corre, pueden pegar el
contenido de esos dos archivos en un worksheet — es el mismo SQL, y es
idempotente. Para verificar que quedó:

```sql
SELECT * FROM business_profiles;
SELECT * FROM users;
```

Deben salir vacías (0 filas) — eso significa que sí existen.


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

# Firma de los tokens de sesión. Si lo dejan vacío el backend genera uno
# aleatorio al arrancar (y avisa con un warning), lo que sirve para
# desarrollar pero invalida todos los tokens en cada reinicio.
# Generen uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET=
```

⚠️ **Este `.env` nunca se sube a git** — ya está en `.gitignore`. Tampoco
lo peguen en el chat general del equipo; si necesitan compartir
credenciales entre ustedes, mándenlas por mensaje directo.

## Paso 6 — Instalar la dependencia nueva y probar

```bash
cd backend
source .venv/bin/activate   # Windows (PowerShell): .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # ya incluye snowflake-connector-python
python -m scripts.migrate         # crea/actualiza las tablas (Paso 3)
uvicorn app.main:app --reload
```

⚠️ `uvicorn` se corre **desde `backend/`**: `config.py` lee `env_file=".env"`
relativo al directorio actual, así que desde la raíz del repo no encuentra
sus credenciales y se va silenciosamente a memoria.

⚠️ En Python 3.13+ hace falta `snowflake-connector-python>=4.x` (el pin del
repo ya es `4.7.3`). Con el pin viejo `3.12.3` pip intenta compilar `cffi`
desde cero y truena con `fatal error C1083: Cannot open include file: 'io.h'`.

En otra terminal:

Los endpoints de perfil piden token del dueño, así que primero se registra un
usuario. El `user_id` que regresa `/auth/register` **es** el `owner_id` del
perfil (el backend responde 403 si intentan escribir el perfil de otro):

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"prueba1","business_name":"Tortas Prueba","full_name":"Persona Prueba","birthdate":"1990-05-20","password":"TortasCalientes26"}'
```


La contraseña tiene que cumplir la política o responde `400` con
`{"detail":{"code":"weak_password","problems":[...]}}`:

| Regla | Código si falla |
|---|---|
| 12 caracteres o más (máximo 128) | `too_short` / `too_long` |
| Al menos una minúscula, una mayúscula y un número | `missing_lowercase` / `missing_uppercase` / `missing_digit` |
| No contener el username | `contains_username` |
| No ser de las más usadas del mundo (`Password1234`, `Qwerty123456`…) | `too_common` |

Ojo con `contains_username`: con el usuario `prueba1`, una contraseña como
`ClavePrueba12` se rechaza porque lo trae adentro.

De la respuesta copien `access_token` y `user.user_id`:

```bash
TOKEN=<access_token>
OWNER=<user_id>

curl -X POST http://localhost:8000/business-profile/$OWNER \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"comida","operating_days":["mon","tue"],"city":"Monterrey","employees":"1","answers":{"se_ha_quedado_sin_stock":true}}'

curl http://localhost:8000/business-profile/$OWNER -H "Authorization: Bearer $TOKEN"

# stats es público a propósito: solo regresa agregados, sin datos de un negocio.
# Con menos de 5 negocios en la categoría llega `answers_pct_true` vacío y
# `below_min_cohort: true`: con una cohorte de uno, cada porcentaje sería la
# respuesta literal de ese negocio. Hace falta más de un perfil para ver el
# desglose — no es un bug.
curl http://localhost:8000/business-profile/stats/comida
```

Si esos comandos regresan datos (no un error), ya está guardando en Snowflake
real. Confírmenlo también directo en Snowsight:

```sql
SELECT * FROM users WHERE username = 'prueba1';
SELECT * FROM business_profiles;
```

⚠️ En `users` van a ver `password_hash`, nunca la contraseña — si ahí aparece
texto legible algo está muy mal y hay que reportarlo de inmediato.

## Si algo falla

| Error / síntoma | Causa probable | Qué hacer |
|---|---|---|
| `250001: Could not connect to Snowflake backend` | Account identifier mal escrito | Revisen que no tenga `.snowflakecomputing.com` al final |
| `Warehouse 'HACKMTY_WH' does not exist or not authorized` | No corrieron el `USE WAREHOUSE` del Paso 3, o el rol no tiene acceso | Vuelvan a correr el Paso 3 completo, en orden |
| El GET regresa `null` pero el POST dijo `"status":"ok"` | El JSON de `answers` no se guardó bien | En Snowsight: `SELECT answers FROM business_profiles WHERE owner_id='prueba1';` |
| La primera llamada tarda varios segundos | Normal — el warehouse estaba "dormido" (`AUTO_SUSPEND`) y despierta solo | Las siguientes llamadas ya son rápidas |
| `Table 'USERS' does not exist` al registrarse | No corrieron las migraciones | `cd backend && python -m scripts.migrate` |
| `python -m scripts.migrate` dice "Snowflake está apagado" | `USE_SNOWFLAKE=false` o `SNOWFLAKE_ACCOUNT` vacío en `backend/.env` | Revisen el Paso 5; si es a propósito, todo bien, están en memoria |
| Los tokens dejan de servir cada vez que reinician el backend | No definieron `JWT_SECRET`, así que se genera uno aleatorio por proceso (sale un warning al arrancar) | Agreguen `JWT_SECRET=<algo largo y aleatorio>` a `backend/.env` |
| Cualquier otro error de conexión | — | Péguenle el mensaje de error completo a Claude Code o Codex, con este archivo de contexto |

## Si de plano no da tiempo

No bloquea nada más del proyecto: dejen `USE_SNOWFLAKE=false` y el resto
de la app sigue funcionando exactamente igual con datos en memoria — se
pierde la elegibilidad para el prize de "Best Use of Snowflake", pero el
producto principal (Capital One) sigue de pie completo.
