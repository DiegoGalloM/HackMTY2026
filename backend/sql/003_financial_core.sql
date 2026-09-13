-- 003_financial_core.sql
-- Núcleo financiero de Capital One Business: catálogo de cuentas, diario,
-- inventario, productos/servicios, ventas, pagos, compras con tarjeta.
--
-- REGLAS DE PORTABILIDAD (este archivo corre igual en Snowflake y en sqlite):
--   * Sólo CREATE TABLE IF NOT EXISTS / CREATE VIEW IF NOT EXISTS.
--   * Tipos: VARCHAR, NUMBER(18,4), INTEGER, BOOLEAN, TIMESTAMP_NTZ.
--     (VARCHAR y no STRING: sqlite le da afinidad TEXT a VARCHAR y NUMERIC a
--     STRING, y con NUMERIC un id que parezca número se guardaría como número.)
--   * Sin DEFAULT con funciones, sin VARIANT/ARRAY, sin índices: las fechas y
--     los ids los pone el backend.
--   * Snowflake NO impone PRIMARY KEY/UNIQUE: la idempotencia (pagos,
--     transacciones de tarjeta) se garantiza en el servicio, no en el DDL.
--
-- Todas las tablas son multi-negocio: business_id = user_id del dueño
-- (el mismo owner_id de business_profiles). Nunca una tabla por usuario.

CREATE TABLE IF NOT EXISTS accounts (
  account_id          VARCHAR,
  business_id         VARCHAR,
  account_number      INTEGER,
  account_name        VARCHAR,
  account_type        VARCHAR,      -- ASSET | LIABILITY | EQUITY | REVENUE | EXPENSE
  account_subtype     VARCHAR,      -- CASH, BANK, INVENTORY, CARD, COGS, ... (ver finance/coa.py)
  normal_balance      VARCHAR,      -- DEBIT | CREDIT
  financial_statement VARCHAR,      -- BALANCE_SHEET | INCOME_STATEMENT
  parent_account_id   VARCHAR,
  is_active           BOOLEAN,
  created_at          TIMESTAMP_NTZ,
  updated_at          TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS journal_entries (
  entry_id           VARCHAR,
  business_id        VARCHAR,
  transaction_number INTEGER,       -- consecutivo por negocio (JE-000123)
  entry_date         VARCHAR,       -- YYYY-MM-DD
  description        VARCHAR,
  source_type        VARCHAR,       -- SALE_COMPLETED | PURCHASE_CAPTURED | ADJUSTMENT | ...
  source_id          VARCHAR,
  status             VARCHAR,       -- POSTED | VOID
  is_adjusting       BOOLEAN,
  total_debit        NUMBER(18,4),
  total_credit       NUMBER(18,4),
  created_at         TIMESTAMP_NTZ,
  posted_at          TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS journal_lines (
  line_id     VARCHAR,
  entry_id    VARCHAR,
  business_id VARCHAR,              -- redundante a propósito: filtrar por tenant sin JOIN
  account_id  VARCHAR,
  line_order  INTEGER,
  debit       NUMBER(18,4),
  credit      NUMBER(18,4),
  memo        VARCHAR
);

CREATE TABLE IF NOT EXISTS inventory_items (
  inventory_item_id VARCHAR,
  business_id       VARCHAR,
  name              VARCHAR,
  unit_of_measure   VARCHAR,        -- kg, unidad, ml, ...
  quantity_on_hand  NUMBER(18,4),
  average_unit_cost NUMBER(18,4),   -- costo promedio ponderado
  reorder_point     NUMBER(18,4),
  is_active         BOOLEAN,
  created_at        TIMESTAMP_NTZ,
  updated_at        TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS inventory_movements (
  movement_id       VARCHAR,
  business_id       VARCHAR,
  inventory_item_id VARCHAR,
  movement_type     VARCHAR,        -- PURCHASE | SALE_CONSUMPTION | ADJUSTMENT | WASTE | INITIAL | REFUND
  quantity_delta    NUMBER(18,4),
  unit_cost         NUMBER(18,4),
  total_cost        NUMBER(18,4),
  quantity_after    NUMBER(18,4),   -- saldo tras el movimiento: reconstruible y auditable
  source_type       VARCHAR,
  source_id         VARCHAR,
  note              VARCHAR,
  occurred_at       TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS sellable_items (
  item_id       VARCHAR,
  business_id   VARCHAR,
  name          VARCHAR,
  description   VARCHAR,
  item_type     VARCHAR,            -- PRODUCT | SERVICE
  selling_price NUMBER(18,4),
  tax_rate      NUMBER(18,4),       -- 0.0825 = 8.25 %
  emoji         VARCHAR,
  is_active     BOOLEAN,
  created_at    TIMESTAMP_NTZ,
  updated_at    TIMESTAMP_NTZ
);

-- Receta / lista de materiales: qué consume cada unidad vendida.
CREATE TABLE IF NOT EXISTS item_components (
  component_id      VARCHAR,
  business_id       VARCHAR,
  item_id           VARCHAR,
  inventory_item_id VARCHAR,
  quantity_per_unit NUMBER(18,4)
);

CREATE TABLE IF NOT EXISTS customers (
  customer_id  VARCHAR,
  business_id  VARCHAR,
  display_name VARCHAR,
  email        VARCHAR,
  phone        VARCHAR,
  created_at   TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS sales_orders (
  order_id       VARCHAR,
  business_id    VARCHAR,
  order_number   INTEGER,
  status         VARCHAR,           -- AWAITING_PAYMENT | PAID | CANCELLED
  subtotal       NUMBER(18,4),
  tax_total      NUMBER(18,4),
  total          NUMBER(18,4),
  currency       VARCHAR,
  customer_id    VARCHAR,
  checkout_token VARCHAR,           -- opaco; es lo único que va en el QR
  note           VARCHAR,
  created_at     TIMESTAMP_NTZ,
  paid_at        TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS order_lines (
  order_line_id VARCHAR,
  business_id   VARCHAR,
  order_id      VARCHAR,
  item_id       VARCHAR,
  item_name     VARCHAR,
  item_type     VARCHAR,
  quantity      NUMBER(18,4),
  unit_price    NUMBER(18,4),
  tax_rate      NUMBER(18,4),
  line_subtotal NUMBER(18,4),
  line_tax      NUMBER(18,4),
  line_total    NUMBER(18,4),
  unit_cost     NUMBER(18,4)        -- costo reconocido al pagar (COGS por línea)
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id      VARCHAR,
  business_id     VARCHAR,
  order_id        VARCHAR,
  provider        VARCHAR,          -- demo | stripe | ...
  provider_ref    VARCHAR,          -- id del cobro en el proveedor (idempotencia)
  amount          NUMBER(18,4),
  currency        VARCHAR,
  method          VARCHAR,          -- card | wallet | cash
  status          VARCHAR,          -- SUCCEEDED | FAILED
  card_last4      VARCHAR,          -- nunca el número completo
  customer_id     VARCHAR,
  created_at      TIMESTAMP_NTZ,
  confirmed_at    TIMESTAMP_NTZ
);

-- Observación cruda de la tarjeta de negocio. NO es un asiento: es lo que el
-- sistema vio. El asiento sale de la clasificación.
CREATE TABLE IF NOT EXISTS card_transactions (
  transaction_id          VARCHAR,
  business_id             VARCHAR,
  provider                VARCHAR,   -- demo | nessie
  provider_transaction_id VARCHAR,
  occurred_at             TIMESTAMP_NTZ,
  amount                  NUMBER(18,4),
  direction               VARCHAR,   -- DEBIT (compra) | CREDIT (abono)
  merchant                VARCHAR,
  description             VARCHAR,
  category_hint           VARCHAR,
  classification_status   VARCHAR,   -- PENDING | NEEDS_REVIEW | CLASSIFIED
  classification_kind     VARCHAR,   -- INVENTORY | EQUIPMENT | EXPENSE | PERSONAL | CARD_PAYMENT
  classified_account_id   VARCHAR,
  confidence              NUMBER(18,4),
  classification_reason   VARCHAR,
  journal_entry_id        VARCHAR,
  receipt_id              VARCHAR,
  created_at              TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS receipts (
  receipt_id     VARCHAR,
  business_id    VARCHAR,
  transaction_id VARCHAR,
  merchant       VARCHAR,
  total          NUMBER(18,4),
  source         VARCHAR,            -- sample | upload | ocr
  received_at    TIMESTAMP_NTZ,
  created_at     TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS receipt_items (
  receipt_item_id   VARCHAR,
  business_id       VARCHAR,
  receipt_id        VARCHAR,
  description       VARCHAR,
  quantity          NUMBER(18,4),
  unit              VARCHAR,
  unit_cost         NUMBER(18,4),
  total_cost        NUMBER(18,4),
  inventory_item_id VARCHAR
);

-- Lo que el negocio le enseña al clasificador: "Restaurant Depot = inventario".
CREATE TABLE IF NOT EXISTS merchant_rules (
  rule_id             VARCHAR,
  business_id         VARCHAR,
  merchant_pattern    VARCHAR,
  classification_kind VARCHAR,
  account_id          VARCHAR,
  created_at          TIMESTAMP_NTZ
);

-- Eventos de negocio normalizados: el eslabón entre "pasó algo" y "se contabilizó".
CREATE TABLE IF NOT EXISTS business_events (
  event_id         VARCHAR,
  business_id      VARCHAR,
  event_type       VARCHAR,          -- SALE_COMPLETED | PURCHASE_CAPTURED | ...
  source_type      VARCHAR,
  source_id        VARCHAR,
  payload          VARCHAR,          -- JSON como texto (portable)
  journal_entry_id VARCHAR,
  created_at       TIMESTAMP_NTZ
);
