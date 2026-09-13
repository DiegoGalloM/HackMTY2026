// Formato de dinero, cantidades y fechas. El negocio opera en EE. UU.: USD.
// Un solo lugar para que no haya una pantalla en pesos y otra en dólares.

export const CURRENCY = "USD";

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: CURRENCY, minimumFractionDigits: 2 });
const moneyWhole = new Intl.NumberFormat("en-US", { style: "currency", currency: CURRENCY, minimumFractionDigits: 0, maximumFractionDigits: 0 });
const qtyFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export function formatMoney(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  return money.format(amount);
}

/** Saldo grande: entero cuando no hay centavos. */
export function formatBalance(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  return amount % 1 === 0 ? moneyWhole.format(amount) : money.format(amount);
}

export function formatQty(quantity: number, unit?: string | null): string {
  const q = qtyFmt.format(quantity);
  return unit ? `${q} ${unit}` : q;
}

export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatChange(pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return "";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = iso.length <= 10 ? new Date(`${iso}T12:00:00`) : new Date(iso);
  return new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short" }).format(date);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(iso));
}

export function ratioValue(value: number | null, unit: string): string {
  if (value === null) return "—";
  if (unit === "%") return formatPct(value);
  if (unit === "$") return formatMoney(value);
  if (unit === "días") return `${value.toFixed(0)} días`;
  return value.toFixed(2);
}
