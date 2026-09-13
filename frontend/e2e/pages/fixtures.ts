/**
 * Respuestas de la API financiera para tests herméticos (sin backend). Sólo
 * los campos que las pantallas leen; el contrato completo vive en
 * src/api/types.ts.
 */

export const SALON_USER = {
  user_id: "usr_demo_salon",
  username: "demo_estetica",
  business_name: "Estética Carolina",
  full_name: "Carolina Ramírez",
  birthdate: "1992-03-21",
};

export const SALON_SESSION = { access_token: "e2e-salon-token", token_type: "bearer", expires_in: 3600, user: SALON_USER };

const ratio = (key: string, label: string, group: string, value: number | null, unit = "x") => ({
  key,
  label,
  group,
  value,
  unit,
  available: value !== null,
  reason: value === null ? "sin datos" : null,
  status: value === null ? "neutral" : "good",
  formula: "a ÷ b",
  explanation: "explicación",
  inputs: {},
});

/** Panel de salud del salón: caja bien, tinte por agotarse, utilidad a la baja. */
export function salonHealth(period = "week") {
  const cash = {
    period: { key: period, start: "2026-09-07", end: "2026-09-13", label: period === "week" ? "esta semana" : "este mes" },
    cash_available: 171436,
    inflows: 12480,
    outflows: 9340,
    net_change: 3140,
    previous_net_change: 5200,
    short_term_obligations: 31240,
    card_balance: 4180,
    tax_payable: 27060,
    working_capital: 158900,
    inventory_tied_up: 18704,
    inventory_share_of_current_assets: 9.8,
    coverage: 5.49,
    status: "good",
    headline: "Tu efectivo cubre lo que debes pronto",
    explanation: "Tienes $171,436.00 disponibles y debes $31,240.00 a corto plazo (tarjeta $4,180.00, impuestos $27,060.00).",
  };
  return {
    period: cash.period,
    revenue: { value: 12480, previous: 15900, change_pct: -21.5 },
    gross_profit: { value: 10820, previous: 13710, change_pct: -21.1 },
    net_income: { value: 4190, previous: 8420, change_pct: -50.2 },
    expenses: { value: 6630, previous: 5290, change_pct: 25.3 },
    orders: { value: 31, previous: 38 },
    average_ticket: 402.58,
    cash,
    liquidity: ratio("current_ratio", "Razón circulante", "liquidez", 6.09),
    margin: ratio("gross_margin", "Margen bruto", "rentabilidad", 86.7, "%"),
    inventory: { value: 18704, item_count: 9, low_stock: ["Tinte (tubo)"], days_inventory: ratio("days_inventory", "Días de inventario", "eficiencia", 61, "días") },
    top_items: [
      { item_id: "i1", name: "Corte de cabello", units: 18, revenue: 4500, cogs: 210, gross_profit: 4290 },
      { item_id: "i2", name: "Manicure gel", units: 9, revenue: 3150, cogs: 190, gross_profit: 2960 },
    ],
    attention: [
      { id: "stock", severity: "attention", title: "Insumos por agotarse", body: "Revisa Tinte (tubo): están en o por debajo de su punto de reorden.", route: "/inventario", lesson: "inventory" },
      { id: "profit_drop", severity: "attention", title: "Tu utilidad bajó frente al periodo anterior", body: "Pregúntale al asistente por qué: compara ventas, costos y gastos.", route: "/asistente", lesson: "margin" },
    ],
    ratios: [
      ratio("current_ratio", "Razón circulante", "liquidez", 6.09),
      ratio("gross_margin", "Margen bruto", "rentabilidad", 86.7, "%"),
      ratio("days_inventory", "Días de inventario", "eficiencia", 61, "días"),
      ratio("debt_to_equity", "Deuda sobre capital", "apalancamiento", 0.2),
    ],
    integrity: { trial_balance_balanced: true, balance_sheet_balanced: true },
  };
}

export function salonOverview() {
  return {
    business_name: SALON_USER.business_name,
    category: "belleza",
    health: salonHealth("month"),
    recent_orders: [],
    recent_purchases: [],
    pending_review: 0,
    has_data: true,
  };
}
