// Funciones tipadas por endpoint. Todas las del negocio cuelgan de
// /business/{ownerId} y llevan el Bearer; las del checkout son públicas.
import { apiFetch, type ApiResult } from "./client";
import type {
  Account,
  AssistantAnswer,
  BalanceSheet,
  CardTransaction,
  CheckoutPayInput,
  CheckoutView,
  ClassificationKind,
  ClassificationSuggestion,
  CustomerSummary,
  DemoBusinessKey,
  Health,
  IncomeStatement,
  Insight,
  InventoryItem,
  InventoryMovement,
  InventorySummary,
  JournalEntry,
  LedgerRow,
  Order,
  Overview,
  ProfitDrivers,
  Ratio,
  SalesSummary,
  SampleReceiptItem,
  SellableItem,
  SellableItemInput,
  Spending,
  TrialBalance,
} from "./types";

export interface BusinessApi {
  ownerId: string;
  overview(): Promise<ApiResult<Overview>>;
  // catálogo
  catalog(): Promise<ApiResult<SellableItem[]>>;
  createCatalogItem(input: SellableItemInput): Promise<ApiResult<SellableItem>>;
  updateCatalogItem(itemId: string, input: Partial<SellableItemInput> & { is_active?: boolean }): Promise<ApiResult<SellableItem>>;
  // inventario
  inventory(): Promise<ApiResult<InventorySummary>>;
  createInventoryItem(input: { name: string; unit_of_measure: string; reorder_point?: number; initial_quantity?: number; initial_unit_cost?: number }): Promise<ApiResult<InventoryItem>>;
  receiveInventory(id: string, input: { quantity: number; unit_cost: number; note?: string }): Promise<ApiResult<InventoryItem>>;
  countInventory(id: string, input: { counted_quantity: number; reason?: string }): Promise<ApiResult<unknown>>;
  movements(inventoryItemId?: string): Promise<ApiResult<InventoryMovement[]>>;
  // ventas
  orders(status?: Order["status"], limit?: number): Promise<ApiResult<Order[]>>;
  createOrder(lines: { item_id: string; quantity: number }[], note?: string): Promise<ApiResult<Order>>;
  order(orderId: string): Promise<ApiResult<Order>>;
  cancelOrder(orderId: string): Promise<ApiResult<Order>>;
  salesSummary(period: string): Promise<ApiResult<SalesSummary>>;
  customers(): Promise<ApiResult<CustomerSummary[]>>;
  // compras
  purchases(status?: CardTransaction["classification_status"]): Promise<ApiResult<CardTransaction[]>>;
  simulatePurchase(scenario?: number): Promise<ApiResult<CardTransaction>>;
  syncPurchases(): Promise<ApiResult<CardTransaction[]>>;
  spending(period: string): Promise<ApiResult<Spending>>;
  suggestion(transactionId: string): Promise<ApiResult<ClassificationSuggestion>>;
  classify(transactionId: string, kind: ClassificationKind, accountId?: string): Promise<ApiResult<CardTransaction>>;
  sampleReceipt(transactionId: string): Promise<ApiResult<SampleReceiptItem[]>>;
  attachReceipt(transactionId: string, items: (SampleReceiptItem & { create_inventory_item?: boolean })[]): Promise<ApiResult<CardTransaction>>;
  // libros
  accounts(): Promise<ApiResult<Account[]>>;
  journal(limit?: number, start?: string, end?: string): Promise<ApiResult<JournalEntry[]>>;
  ledger(): Promise<ApiResult<LedgerRow[]>>;
  trialBalance(adjusted: boolean): Promise<ApiResult<TrialBalance>>;
  incomeStatement(period: string, adjusted?: boolean): Promise<ApiResult<IncomeStatement>>;
  balanceSheet(adjusted?: boolean): Promise<ApiResult<BalanceSheet>>;
  postDepreciation(input: { amount: number; memo?: string }): Promise<ApiResult<JournalEntry>>;
  // análisis
  health(period: string): Promise<ApiResult<Health>>;
  ratios(period: string): Promise<ApiResult<{ period: Health["period"]; ratios: Ratio[] }>>;
  profitDrivers(period: string): Promise<ApiResult<ProfitDrivers>>;
  insights(): Promise<ApiResult<Insight[]>>;
  // asistente
  ask(question: string): Promise<ApiResult<AssistantAnswer>>;
  assistantStatus(): Promise<ApiResult<{ llm_provider: string; llm_available: boolean }>>;
  // demo
  seedDemo(reset?: boolean, business?: DemoBusinessKey): Promise<ApiResult<{ seeded: boolean }>>;
}

export function businessApi(ownerId: string, token: string): BusinessApi {
  const base = `/business/${encodeURIComponent(ownerId)}`;
  const get = <T>(path: string) => apiFetch<T>(`${base}${path}`, { token });
  const post = <T>(path: string, body?: unknown) => apiFetch<T>(`${base}${path}`, { method: "POST", body: body ?? {}, token });
  const patch = <T>(path: string, body: unknown) => apiFetch<T>(`${base}${path}`, { method: "PATCH", body, token });
  const q = (params: Record<string, string | number | boolean | undefined>) => {
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
    return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString()}` : "";
  };

  return {
    ownerId,
    overview: () => get("/overview"),
    catalog: () => get("/catalog"),
    createCatalogItem: (input) => post("/catalog", input),
    updateCatalogItem: (itemId, input) => patch(`/catalog/${itemId}`, input),
    inventory: () => get("/inventory"),
    createInventoryItem: (input) => post("/inventory", input),
    receiveInventory: (id, input) => post(`/inventory/${id}/receive`, input),
    countInventory: (id, input) => post(`/inventory/${id}/count`, input),
    movements: (inventoryItemId) => get(`/inventory/movements${q({ inventory_item_id: inventoryItemId })}`),
    orders: (status, limit) => get(`/orders${q({ status, limit })}`),
    createOrder: (lines, note = "") => post("/orders", { lines, note }),
    order: (orderId) => get(`/orders/${orderId}`),
    cancelOrder: (orderId) => post(`/orders/${orderId}/cancel`),
    salesSummary: (period) => get(`/sales/summary${q({ period })}`),
    customers: () => get("/customers"),
    purchases: (status) => get(`/purchases${q({ status })}`),
    simulatePurchase: (scenario) => post("/purchases/simulate", scenario === undefined ? {} : { scenario }),
    syncPurchases: () => post("/purchases/sync"),
    spending: (period) => get(`/purchases/spending${q({ period })}`),
    suggestion: (transactionId) => get(`/purchases/${transactionId}/suggestion`),
    classify: (transactionId, kind, accountId) => post(`/purchases/${transactionId}/classify`, { kind, account_id: accountId ?? null, remember: true }),
    sampleReceipt: (transactionId) => get(`/purchases/${transactionId}/receipt/sample`),
    attachReceipt: (transactionId, items) => post(`/purchases/${transactionId}/receipt`, { items, source: "sample" }),
    accounts: () => get("/books/accounts"),
    journal: (limit = 100, start, end) => get(`/books/journal${q({ limit, start, end })}`),
    ledger: () => get("/books/ledger"),
    trialBalance: (adjusted) => get(`/books/trial-balance${q({ adjusted })}`),
    incomeStatement: (period, adjusted = true) => get(`/books/income-statement${q({ period, adjusted })}`),
    balanceSheet: (adjusted = true) => get(`/books/balance-sheet${q({ adjusted })}`),
    postDepreciation: (input) => post("/books/depreciation", input),
    health: (period) => get(`/analytics/health${q({ period })}`),
    ratios: (period) => get(`/analytics/ratios${q({ period })}`),
    profitDrivers: (period) => get(`/analytics/profit-drivers${q({ period })}`),
    insights: () => get("/analytics/insights"),
    // Cada pregunta viaja sola: el asistente no guarda conversación.
    ask: (question) => post("/assistant/ask", { question }),
    assistantStatus: () => get("/assistant/status"),
    seedDemo: (reset = false, business) => post(`/demo/seed${q({ reset, business })}`),
  };
}

// ---------------------------------------------------------------- público --

export function getCheckout(token: string): Promise<ApiResult<CheckoutView>> {
  return apiFetch<CheckoutView>(`/pay/${encodeURIComponent(token)}`);
}

export function payCheckout(token: string, input: CheckoutPayInput = {}): Promise<ApiResult<CheckoutView>> {
  return apiFetch<CheckoutView>(`/pay/${encodeURIComponent(token)}`, { method: "POST", body: input });
}

/** Entra con un negocio de ejemplo (lo crea y lo siembra la primera vez). */
export function demoSession(business: DemoBusinessKey = "panaderia"): Promise<ApiResult<{ access_token: string; expires_in: number; user: { user_id: string; username: string; business_name: string; full_name: string; birthdate: string } }>> {
  return apiFetch("/demo/session", { method: "POST", body: { business } });
}
