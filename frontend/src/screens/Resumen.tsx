import { useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, MessageCircle, TrendingDown, TrendingUp } from "lucide-react";
import { formatChange, formatDate, formatMoney, periodBounds } from "../api/format";
import type { JournalEntry } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import { Card, EmptyState, ErrorState, LoadingState, NoSessionState, Notice, SectionTitle, Segmented, StatusPill } from "../components/ui";

type PeriodOpt = "week" | "month" | "30d";

/** Asientos que caben en el diario del resumen; el resto vive en Libros. */
const DIARY_LIMIT = 40;

export const SOURCE_LABELS: Record<string, string> = {
  SALE_COMPLETED: "Venta",
  SALE_COGS: "Costo de venta",
  PURCHASE_CAPTURED: "Compra con tarjeta",
  RECLASSIFICATION: "Reclasificación",
  INVENTORY_ADJUSTMENT: "Ajuste de inventario",
  ADJUSTMENT: "Ajuste",
  OWNER_CONTRIBUTION: "Aportación",
  OWNER_DRAW: "Retiro",
  EXPENSE_PAID: "Gasto pagado",
  MANUAL_RECEIPT: "Entrada manual",
};

/**
 * Resumen: lo que importa (ventas, ganancia, caja, inventario) en lenguaje
 * llano, más el diario del periodo como tabla. Un nivel debajo del asistente;
 * las razones explicadas viven en Libros → Indicadores. Todos los números
 * vienen del backend, derivados del diario.
 */
export default function Resumen() {
  const { api, businessName } = useBusiness();
  const [period, setPeriod] = useState<PeriodOpt>("month");
  const health = useBusinessQuery((a) => a.health(period), [period]);

  if (!api) {
    return (
      <Screen title="Resumen">
        <NoSessionState />
      </Screen>
    );
  }

  const h = health.data;

  return (
    <Screen title="Resumen">
      <div className="px-5">
        <Segmented
          value={period}
          onChange={setPeriod}
          options={[
            { value: "week", label: "Esta semana" },
            { value: "month", label: "Este mes" },
            { value: "30d", label: "30 días" },
          ]}
        />
      </div>

      {health.loading && !h && <LoadingState label="Calculando con tus libros…" />}
      {health.error && <ErrorState error={health.error} onRetry={health.reload} />}

      {h && (
        <>
          {h.revenue.value === 0 && h.orders.value === 0 && (
            <div className="mt-4 px-5">
              <EmptyState title={`Sin ventas ${h.period.label}`} body="En cuanto cobres con QR o registres compras, aquí verás cómo va el negocio." action={<Link to="/vender" className="text-sm font-semibold text-brand">Ir a Vender</Link>} />
            </div>
          )}

          <section className="mt-4 grid grid-cols-2 gap-3 px-5">
            <MetricCard label={`Ventas ${h.period.label}`} value={h.revenue.value} change={h.revenue.change_pct} />
            <MetricCard label="Ganancia neta" value={h.net_income.value} change={h.net_income.change_pct} tone />
            <Card>
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted">Caja</p>
                <StatusPill status={h.cash.status} />
              </div>
              <p className="mt-1 text-lg font-semibold tabular-nums">{formatMoney(h.cash.cash_available)}</p>
              <p className="text-[11px] text-muted">debes pronto {formatMoney(h.cash.short_term_obligations)}</p>
            </Card>
            <Card>
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted">Inventario</p>
                <StatusPill status={h.inventory.low_stock.length ? "attention" : h.inventory.days_inventory.status} />
              </div>
              <p className="mt-1 text-lg font-semibold tabular-nums">{formatMoney(h.inventory.value)}</p>
              <p className="text-[11px] text-muted">{h.inventory.low_stock.length ? `${h.inventory.low_stock.length} por agotarse` : `${h.inventory.item_count} insumos`}</p>
            </Card>
          </section>

          <section className="mt-5 px-5">
            <Card>
              <p className="text-sm font-semibold">{h.cash.headline}</p>
              <p className="mt-1 text-xs text-muted">{h.cash.explanation}</p>
              <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
                <div className="rounded-xl bg-tile py-2">
                  <p className="text-muted">Entró</p>
                  <p className="font-semibold text-positive tabular-nums">{formatMoney(h.cash.inflows)}</p>
                </div>
                <div className="rounded-xl bg-tile py-2">
                  <p className="text-muted">Salió</p>
                  <p className="font-semibold tabular-nums">{formatMoney(h.cash.outflows)}</p>
                </div>
                <div className="rounded-xl bg-tile py-2">
                  <p className="text-muted">En inventario</p>
                  <p className="font-semibold tabular-nums">{formatMoney(h.cash.inventory_tied_up)}</p>
                </div>
              </div>
            </Card>
          </section>

          {h.attention.length > 0 && (
            <section className="mt-6 px-5">
              <SectionTitle>Necesita tu atención</SectionTitle>
              <ul className="space-y-2">
                {h.attention.map((a) => (
                  <li key={a.id}>
                    <Link to={a.route} className="block rounded-2xl bg-white px-4 py-3 ring-1 ring-black/5">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold">{a.title}</p>
                        <StatusPill status={a.severity} />
                      </div>
                      <p className="mt-1 text-xs text-muted">{a.body}</p>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {h.top_items.length > 0 && (
            <section className="mt-6 px-5">
              <SectionTitle>Lo que más te deja</SectionTitle>
              <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white ring-1 ring-black/5">
                {h.top_items.map((i) => (
                  <li key={i.item_id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <span>
                      {i.name} <span className="text-xs text-muted">· {Math.round(i.units)} uds</span>
                    </span>
                    <span className="font-semibold tabular-nums text-positive">{formatMoney(i.gross_profit)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <DiarySection period={period} />

          <section className="mt-6 px-5">
            <div className="grid grid-cols-2 gap-2">
              <Link to="/analisis" className="flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand text-sm font-semibold text-white">
                <MessageCircle size={16} aria-hidden /> Preguntar
              </Link>
              <Link to="/libros" className="flex min-h-11 items-center justify-center gap-2 rounded-full bg-tile text-sm font-semibold">
                <BookOpen size={16} aria-hidden /> Ver mis libros
              </Link>
            </div>
            <div className="mt-3">
              {h.integrity.trial_balance_balanced && h.integrity.balance_sheet_balanced ? (
                <Notice tone="success">Los libros de {businessName} cuadran: balanza y balance verificados.</Notice>
              ) : (
                <ErrorState error={{ ok: false, kind: "unexpected", message: "Los libros NO cuadran. Es un error de integridad y no se oculta: revisa el diario." }} />
              )}
            </div>
          </section>
        </>
      )}
    </Screen>
  );
}

function MetricCard({ label, value, change, tone }: { label: string; value: number; change: number | null; tone?: boolean }) {
  const up = (change ?? 0) >= 0;
  return (
    <Card>
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${tone && value < 0 ? "text-accent" : ""}`}>{formatMoney(value)}</p>
      {change !== null ? (
        <p className={`flex items-center gap-1 text-[11px] ${up ? "text-positive" : "text-accent"}`}>
          {up ? <TrendingUp size={12} aria-hidden /> : <TrendingDown size={12} aria-hidden />}
          {formatChange(change)} vs. periodo anterior
        </p>
      ) : (
        <p className="text-[11px] text-muted">sin periodo anterior</p>
      )}
    </Card>
  );
}

/**
 * Diario del periodo como tabla: una fila por línea de asiento, agrupadas
 * bajo un encabezado por asiento (JE · fecha · descripción), los abonos
 * sangrados. El inventario aparece sólo como su cuenta; el detalle por
 * insumo vive en Inventario. El mismo rango que el resumen, calculado aquí
 * con la misma regla que el backend.
 */
function DiarySection({ period }: { period: PeriodOpt }) {
  const { start, end } = periodBounds(period);
  const journal = useBusinessQuery((a) => a.journal(DIARY_LIMIT, start, end), [start, end]);
  const entries = journal.data ?? [];
  return (
    <section className="mt-6 px-5">
      <SectionTitle>Diario</SectionTitle>
      {journal.loading && !journal.data && <LoadingState label="Leyendo el diario…" />}
      {journal.error && <ErrorState error={journal.error} onRetry={journal.reload} />}
      {journal.data && entries.length === 0 && <p className="text-sm text-muted">Sin asientos en este periodo.</p>}
      {entries.length > 0 && (
        <div className="overflow-hidden rounded-2xl bg-white ring-1 ring-black/5">
          {/* overflow-x-auto por si un importe muy largo no cabe: el marco del
              celular nunca scrollea a lo ancho. Con anchos normales las cinco
              columnas caben en los 322 px útiles y no hay que deslizar. */}
          <div className="no-scrollbar overflow-x-auto">
            <table className="w-full text-[11px]" data-testid="diary-table">
              <thead>
                <tr className="text-muted">
                  <th className="px-2 py-2 text-left font-medium">Fecha</th>
                  <th className="px-1 py-2 text-left font-medium">Concepto</th>
                  <th className="px-1 py-2 text-left font-medium">Cuenta</th>
                  <th className="px-1 py-2 text-right font-medium">Debe</th>
                  <th className="px-2 py-2 text-right font-medium">Haber</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e: JournalEntry) => (
                  <EntryRows key={e.entry_id} entry={e} />
                ))}
              </tbody>
            </table>
          </div>
          <p className="border-t border-black/5 px-3 py-2 text-[11px] text-muted">
            {entries.length >= DIARY_LIMIT ? `Los ${DIARY_LIMIT} asientos más recientes del periodo. ` : ""}
            <Link to="/libros" className="font-semibold text-brand">
              Ver todo en Libros
            </Link>
          </p>
        </div>
      )}
    </section>
  );
}

function EntryRows({ entry }: { entry: JournalEntry }) {
  return (
    <>
      <tr className="border-t border-black/5 bg-tile/60">
        <td colSpan={5} className="px-2 py-1.5 font-semibold text-ink">
          JE-{String(entry.transaction_number).padStart(5, "0")} · {formatDate(entry.entry_date)} · {entry.description}
          <span className="ml-1 font-normal text-muted">({SOURCE_LABELS[entry.source_type] ?? entry.source_type}{entry.is_adjusting ? " · ajuste" : ""})</span>
        </td>
      </tr>
      {entry.lines.map((l) => (
        <tr key={l.line_id} className="align-top">
          <td className="w-11 px-2 py-1 whitespace-nowrap text-[10px] text-muted tabular-nums">{formatDate(entry.entry_date)}</td>
          <td className="max-w-[4.5rem] truncate px-1 py-1 text-muted">{l.memo || SOURCE_LABELS[entry.source_type] || entry.source_type}</td>
          {/* Los abonos van sangrados, como en el diario de Libros. */}
          <td className={`max-w-[6.5rem] px-1 py-1 break-words ${l.credit > 0 ? "pl-4" : ""}`}>
            <span className="mr-1 text-muted tabular-nums">{l.account_number}</span>
            {l.account_name}
          </td>
          <td className="px-1 py-1 text-right whitespace-nowrap tabular-nums">{l.debit > 0 ? formatMoney(l.debit) : ""}</td>
          <td className="px-2 py-1 text-right whitespace-nowrap tabular-nums">{l.credit > 0 ? formatMoney(l.credit) : ""}</td>
        </tr>
      ))}
    </>
  );
}
