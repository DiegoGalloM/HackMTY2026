// Formato de dinero, cantidades y fechas. Un solo lugar para todas las
// pantallas. El símbolo es "$" sin código de moneda a propósito: la panadería
// demo opera en dólares y la estética en pesos, y las dos se leen igual. No
// hay soporte multi-moneda (ver docs/PROJECT_STATUS.md).

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

/**
 * Rango de fechas de un periodo, igual que `period_bounds` del backend
 * (inclusivo, fecha UTC de hoy). Sirve para pedir el diario del mismo rango
 * que el resumen sin un viaje extra al servidor.
 */
export function periodBounds(period: string): { start: string; end: string } {
  const today = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  const utc = (y: number, m: number, d: number) => new Date(Date.UTC(y, m, d));
  const y = today.getUTCFullYear();
  const m = today.getUTCMonth();
  const d = today.getUTCDate();
  const end = iso(utc(y, m, d));
  const daysAgo = (n: number) => iso(utc(y, m, d - n));
  switch (period) {
    case "today":
      return { start: end, end };
    case "yesterday":
      return { start: daysAgo(1), end: daysAgo(1) };
    case "week": {
      const weekday = (today.getUTCDay() + 6) % 7; // lunes = 0
      return { start: daysAgo(weekday), end };
    }
    case "last_week": {
      const weekday = (today.getUTCDay() + 6) % 7;
      return { start: daysAgo(weekday + 7), end: daysAgo(weekday + 1) };
    }
    case "month":
      return { start: iso(utc(y, m, 1)), end };
    case "last_month":
      return { start: iso(utc(y, m - 1, 1)), end: iso(utc(y, m, 0)) };
    case "7d":
      return { start: daysAgo(6), end };
    case "30d":
      return { start: daysAgo(29), end };
    case "90d":
      return { start: daysAgo(89), end };
    case "year":
      return { start: iso(utc(y, 0, 1)), end };
    default:
      return { start: "2000-01-01", end };
  }
}

export function ratioValue(value: number | null, unit: string): string {
  if (value === null) return "—";
  if (unit === "%") return formatPct(value);
  if (unit === "$") return formatMoney(value);
  if (unit === "días") return `${value.toFixed(0)} días`;
  return value.toFixed(2);
}
