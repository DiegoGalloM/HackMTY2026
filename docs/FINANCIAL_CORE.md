# Núcleo financiero — cómo está construido

> Rigor contable abajo, cero fricción arriba. Este documento es el mapa para
> quien toque `backend/app/finance`, las migraciones 003/004 o las pantallas
> financieras del frontend.

## Un solo flujo de verdad

```
evento real                 QR pagado · compra con la tarjeta · conteo de inventario
      ↓
evento normalizado          PaymentEvent · NormalizedTransaction · ajuste
      ↓
motor de inventario         inventory_items + inventory_movements (costo promedio ponderado)
motor contable              journal_entries + journal_lines (partida doble, balanceado siempre)
      ↓
Snowflake / sqlite          tablas multi-negocio con business_id (migraciones 003, 004)
      ↓
derivados                   v_general_ledger, v_account_balances → balanza, resultados, balance
      ↓
analítica                   razones, salud de caja, drivers de utilidad (backend, nunca React)
      ↓
API → frontend → asistente  explicación en lenguaje llano; el LLM sólo redacta
```

## Capa de datos (`backend/app/db`)

| Pieza | Qué hace |
|---|---|
| `Database` (`base.py`) | Interfaz mínima: `execute`, `rows`, `execute_many`, `transaction()`, `ensure_schema()`. Placeholders `:nombre`. |
| `SqliteDatabase` | `USE_SNOWFLAKE=false`: sqlite en memoria (o archivo con `LOCAL_DB_PATH`). Tests y demo sin red. |
| `SnowflakeDatabase` | Pool de 4 conexiones persistentes, autocommit, `BEGIN/COMMIT` explícito en transacciones, inserciones multi-fila. |
| `sql/003_financial_core.sql` | 16 tablas. SQL portable: `VARCHAR`, `NUMBER(18,4)`, `BOOLEAN`, `TIMESTAMP_NTZ`; sin defaults con funciones ni VARIANT. |
| `sql/004_financial_views.sql` | `v_general_ledger` (líneas + cuenta + encabezado) y `v_account_balances`. Derivadas, nunca editables. |

Las migraciones se aplican solas: en sqlite al crear la base; en Snowflake al
arrancar el backend (`scripts/migrate.apply_pending`, misma tabla
`schema_migrations` del runner manual `python -m scripts.migrate`).

## Tablas (todas con `business_id` = `user_id` del dueño)

`accounts`, `journal_entries`, `journal_lines`, `inventory_items`,
`inventory_movements`, `sellable_items`, `item_components` (receta),
`customers`, `sales_orders`, `order_lines`, `payments`, `card_transactions`,
`receipts`, `receipt_items`, `merchant_rules`, `business_events`.

Nunca una tabla por usuario. Snowflake no impone PRIMARY KEY/UNIQUE: la
idempotencia vive en los servicios (pago por `provider_ref`, asiento por
`(source_type, source_id)`, transacción por `provider_transaction_id`).

## Servicios (`backend/app/finance`)

| Módulo | Responsabilidad | Invariantes que impone |
|---|---|---|
| `coa.py` | Plantilla del catálogo (1000 activos … 5000 gastos) + extras por giro del onboarding. | Tipo, saldo normal y estado financiero por cuenta. |
| `accounting.py` | Asientos, mayor, balanza (ajustada / sin ajustes), resultados, balance. | Σ debe = Σ haber; una línea es debe **o** haber; sin negativos; no se publica dos veces el mismo origen; balanza que no cuadra se registra como `INTEGRITY_ERROR`, nunca se oculta. |
| `inventory.py` | Existencias, costo promedio ponderado, bitácora, conteos. | Ningún cambio de cantidad sin `inventory_movement`; el saldo se reconstruye sumando la bitácora. |
| `catalog.py` | Productos/servicios con receta; costo estimado y unidades producibles. | Una receta pertenece al negocio. |
| `sales.py` | Órdenes, token opaco del QR, `complete_payment()`. | Sólo un `PaymentEvent` SUCCEEDED produce efectos; todo en una transacción; idempotente por `provider_ref` y por orden; el monto debe coincidir. |
| `payments.py` | `PaymentProvider` (demo). | El evento es el mismo que produciría un webhook real. Nunca se guarda el número de tarjeta. |
| `purchases.py` | `TransactionProvider` (demo, Nessie), normalización, clasificación por reglas + memoria del negocio, tickets. | Se contabiliza al instante (el lado de la tarjeta es cierto); corregir = reclasificación, nunca editar. |
| `analytics.py` | Razones, salud de caja, drivers de utilidad, insights de educación. | Cada razón dice si está disponible y por qué no; nada de ceros inventados. |
| `assistant.py` | Intención → herramientas → conocimiento → redacción. Sin estado: cada pregunta se responde sola. | Las cifras vienen de `evidence`; el LLM no puede introducir montos nuevos (guardia). |
| `knowledge.py` | Corpus de educación financiera + perfil del onboarding; recuperación léxica. | Explica, no calcula. |
| `llm.py` | Anthropic (`claude-opus-5`) → Snowflake Cortex (`claude-sonnet-4-5`) → plantillas. | Opcional y reemplazable. |
| `demo.py` | Registro `DEMO_BUSINESSES` (Panadería La Espiga, Estética Carolina): 10 semanas por negocio construidas con la misma tubería (`Pipeline`), copiadas en bloque. | Reutiliza el catálogo de cuentas existente; nunca lo duplica. La panadería es reproducible al centavo (test). |
| `repo.py` | Acceso a tablas acotado a un `business_id`. | Toda consulta libre debe llevar `:business_id`. |

## Asientos que genera cada evento

| Evento | Asiento |
|---|---|
| Venta pagada ($50 + $4 impuesto, costo $8.80) | DR Banco 54 / CR Ventas 50 / CR Impuesto por pagar 4 · DR Costo de ventas 8.80 / CR Inventario 8.80 |
| Compra con tarjeta (inventario) | DR Inventario / CR Tarjeta de crédito del negocio |
| Compra con tarjeta (equipo, gasto, personal) | DR Equipo · Gasto · Retiros del dueño / CR Tarjeta |
| Corrección del dueño | DR cuenta nueva / CR cuenta vieja (`RECLASSIFICATION`) |
| Pago de la tarjeta | DR Tarjeta / CR Banco |
| Conteo con merma | DR Mermas y ajustes / CR Inventario (`is_adjusting`) |
| Depreciación | DR Depreciación / CR Depreciación acumulada (`is_adjusting`) |
| Inventario inicial | DR Inventario / CR Capital del dueño |

Balanza sin ajustes = asientos con `is_adjusting = false`; balanza ajustada =
todos. El balance general presenta la utilidad acumulada dentro del capital
(no hay asientos de cierre) y verifica `Activos = Pasivos + Capital`.

## Asistente: una pregunta, una respuesta

El asistente no es un RAG libre: es un **enrutador de intenciones** por regex
(`INTENT_PATTERNS`, `PERIOD_PATTERNS`) que elige una herramienta `_tool_*`
sobre el motor, agrega recuperación léxica para conceptos y deja que el LLM
sólo *redacte* la respuesta con la evidencia como hechos.

**No hay conversación.** Cada llamada a `Assistant.ask(question)` es
independiente: el servidor no guarda estado y el cliente no manda historial.
Todo lo que necesita para responder sale de la pregunta actual — intención,
periodo (`month` por defecto) y, cuando la herramienta trabaja sobre un
insumo, el insumo que la pregunta nombra (`_find_inventory_item`). Una
continuación como "¿y el mes pasado?" no tiene de dónde heredar y cae en la
respuesta de respaldo, a propósito.

> Se implementó una memoria de sesión (historial del cliente, herencia de
> intención/periodo/entidad y reformulación por LLM) y se retiró después por
> decisión de producto. Si vuelve a hacer falta, el punto de entrada es
> `ask()` y el contrato sería un `history` en `AssistantAsk`.

**El LLM sólo redacta.** `_rewrite` recibe la pregunta, los hechos y la
respuesta base, y devuelve una versión más cálida. La **guardia de cifras**
descarta la reescritura completa si aparece un número (monto, porcentaje,
cantidad o días, comparado por valor) o una palabra de magnitud ("millón") que
no esté en la evidencia o en la respuesta base. Así el LLM no puede introducir
números nuevos ni por error ni por inyección. Sin proveedor disponible
(`NoLLM`) la respuesta es la plantilla determinista y todo sigue funcionando.

## Seguridad por negocio

- `require_owner` (`routers/deps.py`) protege estructuralmente todo
  `/business/{owner_id}/…`: el `owner_id` del path debe ser el `sub` del token.
- `FinanceContext` se construye con ese `owner_id`; todos los servicios y el
  asistente nacen atados a un `Repo` de ese negocio. No existe una herramienta
  del asistente que reciba `business_id`.
- La única ruta pública, `/pay/{token}`, localiza la orden por un token de 256
  bits y desde ahí opera con el `Repo` de ese negocio.

## Rendimiento en Snowflake

Cada consulta cuesta ~0.3–0.5 s de ida y vuelta. Por eso:

- una instantánea del mayor por request (`AccountingService.snapshot()`), de la
  que salen todos los saldos, balanzas, estados y flujos;
- órdenes pagadas y sus líneas se leen una vez por request;
- hidratación en lote (líneas, pagos, clientes, tickets);
- catálogo de cuentas, perfil y usuario en caché con TTL de 2 minutos,
  invalidada por las escrituras;
- pool de conexiones para que varias pantallas consulten en paralelo;
- la semilla se construye en sqlite y se copia con inserciones multi-fila.

Con eso un panel completo tarda 2–4 s en Snowflake y milisegundos en sqlite.

## Pruebas

`backend/tests/test_finance_engine.py` (invariantes contables e inventario),
`test_finance_api.py` (flujo completo por HTTP: catálogo → orden → QR → pago
público → libros → análisis → asistente, y guardia de tenant),
`test_assistant.py` (enrutamiento, cifras del motor, aislamiento, guardia del
LLM), `test_demo.py` (las dos demos: libros que cuadran, insumo por agotarse,
causa real de la caída de utilidad, idempotencia, la panadería reproducible al
centavo con fecha fija, que ninguna demo deje existencias negativas sin
importar la fecha en que se siembre, y que las cuentas demo existan sin pasar
por "Explorar la demo"). La historia demo termina "hoy": un test que compare
contra "esta semana" o "este mes" tiene que aguantar cualquier día o fijar la
fecha. Todo corre contra sqlite en memoria; Snowflake se
verifica a mano con el backend real (ver `docs/DEMO.md`).
