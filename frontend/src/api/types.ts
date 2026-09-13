// Contratos de la API financiera. Espejo de lo que producen los servicios de
// backend/app/finance (dicts pasados por `jsonable`: Decimal -> number).
// Si cambia una forma allá, cambia aquí: es el único lugar del frontend que
// describe estas entidades.

export type Status = "good" | "attention" | "critical" | "neutral" | "info";
export type PeriodKey = "today" | "yesterday" | "week" | "last_week" | "month" | "last_month" | "7d" | "30d" | "90d" | "year" | "all";

export interface Period {
  key: string;
  start: string;
  end: string;
  label: string;
}

// --------------------------------------------------------------- cuentas --

export interface Account {
  account_id: string;
  account_number: number;
  account_name: string;
  account_type: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE";
  account_subtype: string;
  normal_balance: "DEBIT" | "CREDIT";
  financial_statement: "BALANCE_SHEET" | "INCOME_STATEMENT";
  is_active: boolean;
}

export interface JournalLine {
  line_id: string;
  account_id: string;
  account_number: number;
  account_name: string;
  line_order: number;
  debit: number;
  credit: number;
  memo: string;
}

export interface JournalEntry {
  entry_id: string;
  transaction_number: number;
  entry_date: string;
  description: string;
  source_type: string;
  source_id: string;
  status: string;
  is_adjusting: boolean;
  total_debit: number;
  total_credit: number;
  posted_at: string;
  lines: JournalLine[];
}

export interface LedgerRow extends Account {
  total_debits: number;
  total_credits: number;
  balance: number;
}

export interface TrialBalance {
  as_of: string | null;
  adjusted: boolean;
  rows: (Account & { debit_balance: number; credit_balance: number })[];
  total_debit: number;
  total_credit: number;
  balanced: boolean;
}

export interface StatementRow extends Account {
  amount: number;
}

export interface IncomeStatement {
  start: string | null;
  end: string | null;
  adjusted: boolean;
  revenue: StatementRow[];
  cogs: StatementRow[];
  operating_expenses: StatementRow[];
  total_revenue: number;
  total_cogs: number;
  gross_profit: number;
  total_operating_expenses: number;
  net_income: number;
}

export interface BalanceSheet {
  as_of: string | null;
  adjusted: boolean;
  assets: StatementRow[];
  liabilities: StatementRow[];
  equity: StatementRow[];
  current_earnings: number;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  balanced: boolean;
  difference: number;
}

// ------------------------------------------------------------ inventario --

export interface InventoryItem {
  inventory_item_id: string;
  name: string;
  unit_of_measure: string;
  quantity_on_hand: number;
  average_unit_cost: number;
  reorder_point: number;
  is_active: boolean;
  inventory_value: number;
  low_stock: boolean;
}

export interface InventoryMovement {
  movement_id: string;
  inventory_item_id: string;
  item_name: string | null;
  unit_of_measure: string | null;
  movement_type: "PURCHASE" | "SALE_CONSUMPTION" | "ADJUSTMENT" | "WASTE" | "INITIAL" | "REFUND";
  quantity_delta: number;
  unit_cost: number;
  total_cost: number;
  quantity_after: number;
  source_type: string;
  source_id: string;
  note: string;
  occurred_at: string;
}

export interface InventorySummary {
  item_count: number;
  total_value: number;
  low_stock_items: InventoryItem[];
  items: InventoryItem[];
}

// --------------------------------------------------------------- catálogo --

export interface ItemComponent {
  component_id: string;
  inventory_item_id: string;
  quantity_per_unit: number;
  inventory_item_name: string;
  unit_of_measure: string;
  average_unit_cost: number;
  quantity_on_hand: number;
}

export interface SellableItem {
  item_id: string;
  name: string;
  description: string;
  item_type: "PRODUCT" | "SERVICE";
  selling_price: number;
  tax_rate: number;
  emoji: string;
  is_active: boolean;
  components: ItemComponent[];
  estimated_unit_cost: number;
  estimated_margin: number;
  estimated_margin_pct: number | null;
  producible_units: number | null;
}

export interface SellableItemInput {
  name: string;
  item_type: "PRODUCT" | "SERVICE";
  selling_price: number;
  description?: string;
  tax_rate?: number;
  emoji?: string;
  components: { inventory_item_id: string; quantity_per_unit: number }[];
}

// ----------------------------------------------------------------- ventas --

export interface OrderLine {
  order_line_id: string;
  item_id: string;
  item_name: string;
  item_type: "PRODUCT" | "SERVICE";
  quantity: number;
  unit_price: number;
  tax_rate: number;
  line_subtotal: number;
  line_tax: number;
  line_total: number;
  unit_cost: number | null;
}

export interface Payment {
  payment_id: string;
  provider: string;
  provider_ref: string;
  amount: number;
  status: "SUCCEEDED" | "FAILED";
  method: string;
  card_last4: string | null;
  confirmed_at: string | null;
}

export interface Customer {
  customer_id: string;
  display_name: string;
  email: string | null;
  phone: string | null;
}

export interface Order {
  order_id: string;
  order_number: number;
  status: "AWAITING_PAYMENT" | "PAID" | "CANCELLED";
  subtotal: number;
  tax_total: number;
  total: number;
  currency: string;
  checkout_token: string;
  note: string;
  created_at: string;
  paid_at: string | null;
  lines: OrderLine[];
  payment: Payment | null;
  customer: Customer | null;
}

export interface SalesByItem {
  item_id: string;
  name: string;
  units: number;
  revenue: number;
  cogs: number;
  gross_profit: number;
}

export interface SalesSummary {
  start: string | null;
  end: string | null;
  label: string;
  order_count: number;
  units_sold: number;
  revenue: number;
  tax_collected: number;
  cash_collected: number;
  cogs: number;
  gross_profit: number;
  gross_margin_pct: number | null;
  average_ticket: number | null;
  by_item: SalesByItem[];
  by_day: { day: string; orders: number; revenue: number }[];
}

export interface CustomerSummary extends Customer {
  purchase_count: number;
  lifetime_revenue: number;
  first_purchase: string | null;
  last_purchase: string | null;
  average_order_value: number | null;
}

/** Lo que ve el cliente en /pay/:token. Sin datos del negocio más allá del nombre. */
export interface CheckoutView {
  business_name: string;
  order_number: number;
  status: Order["status"];
  currency: string;
  lines: { item_name: string; quantity: number; unit_price: number; line_total: number }[];
  subtotal: number;
  tax_total: number;
  total: number;
  paid_at: string | null;
  payment: { card_last4: string | null; provider: string; confirmed_at: string | null } | null;
  provider: { provider: string; mode: "test" | "live" };
  already_paid?: boolean;
}

export interface CheckoutPayInput {
  card_last4?: string;
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  simulate?: "success" | "fail";
}

// ---------------------------------------------------------------- compras --

export type ClassificationKind = "INVENTORY" | "EQUIPMENT" | "EXPENSE" | "PERSONAL" | "CARD_PAYMENT";

export interface ReceiptItem {
  receipt_item_id: string;
  description: string;
  quantity: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
  inventory_item_id: string | null;
}

export interface Receipt {
  receipt_id: string;
  merchant: string;
  total: number;
  source: string;
  items: ReceiptItem[];
}

export interface CardTransaction {
  transaction_id: string;
  provider: string;
  provider_transaction_id: string;
  occurred_at: string;
  amount: number;
  direction: "DEBIT" | "CREDIT";
  merchant: string;
  description: string;
  classification_status: "PENDING" | "NEEDS_REVIEW" | "CLASSIFIED";
  classification_kind: ClassificationKind | null;
  classified_account_id: string | null;
  account_name: string | null;
  kind_label: string | null;
  confidence: number | null;
  classification_reason: string | null;
  journal_entry_id: string | null;
  receipt_id: string | null;
  receipt: Receipt | null;
  sample_receipt_available: boolean;
  needs_review: boolean;
}

export interface ClassificationSuggestion {
  kind: ClassificationKind;
  kind_label: string;
  account_id: string;
  account_name: string;
  confidence: number;
  reason: string;
  requires_user_confirmation: boolean;
}

export interface SampleReceiptItem {
  description: string;
  quantity: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
  inventory_item_id: string | null;
  inventory_item_name: string | null;
  suggested_name: string;
}

export interface Spending {
  label: string;
  transaction_count: number;
  total: number;
  by_merchant: { merchant: string; amount: number }[];
  by_kind: { kind: string; label: string; amount: number }[];
  by_account: { account_name: string; account_subtype: string; amount: number }[];
  pending_review: number;
}

// --------------------------------------------------------------- análisis --

export interface Ratio {
  key: string;
  label: string;
  group: "liquidez" | "rentabilidad" | "apalancamiento" | "eficiencia";
  value: number | null;
  unit: "x" | "%" | "$" | "días";
  available: boolean;
  reason: string | null;
  status: Status;
  formula: string;
  explanation: string;
  inputs: Record<string, number>;
}

export interface CashIntelligence {
  period: Period;
  cash_available: number;
  inflows: number;
  outflows: number;
  net_change: number;
  previous_net_change: number;
  short_term_obligations: number;
  card_balance: number;
  tax_payable: number;
  working_capital: number;
  inventory_tied_up: number;
  inventory_share_of_current_assets: number | null;
  coverage: number | null;
  status: Status;
  headline: string;
  explanation: string;
}

export interface Delta {
  value: number;
  previous: number;
  change_pct: number | null;
}

export interface AttentionItem {
  id: string;
  severity: Status;
  title: string;
  body: string;
  route: string;
  lesson: "cash" | "margin" | "inventory" | null;
}

export interface Health {
  period: Period;
  revenue: Delta;
  gross_profit: Delta;
  net_income: Delta;
  expenses: Delta;
  orders: { value: number; previous: number };
  average_ticket: number | null;
  cash: CashIntelligence;
  liquidity: Ratio;
  margin: Ratio;
  inventory: { value: number; item_count: number; low_stock: string[]; days_inventory: Ratio };
  top_items: SalesByItem[];
  attention: AttentionItem[];
  ratios: Ratio[];
  integrity: { trial_balance_balanced: boolean; balance_sheet_balanced: boolean };
}

export interface ProfitDriver {
  driver: "revenue" | "cogs" | "expenses";
  label: string;
  impact: number;
  detail: string;
}

export interface ProfitDrivers {
  period: Period;
  net_income: number;
  previous_net_income: number;
  delta: number;
  revenue: number;
  previous_revenue: number;
  cogs: number;
  previous_cogs: number;
  operating_expenses: number;
  previous_operating_expenses: number;
  gross_margin_pct: number | null;
  previous_gross_margin_pct: number | null;
  drivers: ProfitDriver[];
  expense_changes: { account_name: string; current: number; previous: number; delta: number }[];
  product_changes: { name: string; units: number; previous_units: number; gross_profit: number; previous_gross_profit: number; delta: number }[];
}

export interface Insight {
  id: string;
  lesson: "cash" | "margin" | "inventory";
  title: string;
  body: string;
  action: string;
  evidence: Record<string, unknown>;
}

export interface Overview {
  business_name: string;
  category: string | null;
  health: Health;
  recent_orders: Order[];
  recent_purchases: CardTransaction[];
  pending_review: number;
  has_data: boolean;
}

// -------------------------------------------------------------- asistente --

export interface Evidence {
  label: string;
  value: string;
  detail?: string;
}

export interface AssistantAnswer {
  question: string;
  answer: string;
  intent: string;
  language: "es" | "en";
  period: string;
  evidence: Evidence[];
  sources: { type: "structured" | "knowledge"; id?: string; title: string }[];
  tool_calls: string[];
  suggestions: string[];
  llm_used: boolean;
  llm_provider: string | null;
}
