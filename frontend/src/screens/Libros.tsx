import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { formatDate, formatMoney, ratioValue } from "../api/format";
import type { JournalEntry, Ratio, StatementRow } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import { Card, ErrorState, LoadingState, NoSessionState, Notice, Segmented, StatusPill } from "../components/ui";

type Tab = "resultados" | "balance" | "diario" | "balanza" | "indicadores";
type PeriodOpt = "month" | "last_month" | "30d" | "all";

const GROUPS: { key: Ratio["group"]; label: string }[] = [
  { key: "liquidez", label: "Liquidez: ¿puedes pagar lo que debes pronto?" },
  { key: "rentabilidad", label: "Rentabilidad: ¿te queda ganancia?" },
  { key: "eficiencia", label: "Inventario: ¿tu dinero se mueve?" },
  { key: "apalancamiento", label: "Deuda: ¿de quién es el negocio?" },
];

const PERIODS: { value: PeriodOpt; label: string }[] = [
  { value: "month", label: "Este mes" },
  { value: "last_month", label: "Mes pasado" },
  { value: "30d", label: "30 días" },
  { value: "all", label: "Todo" },
];

const SOURCE_LABELS: Record<string, string> = {
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
 * Libros: la contabilidad formal, disponible para quien quiera verla.
 * Todo viene derivado del diario en el backend; aquí solo se presenta.
 */
export default function Libros() {
  const { api } = useBusiness();
  const [tab, setTab] = useState<Tab>("resultados");
  const [period, setPeriod] = useState<PeriodOpt>("month");
  const [adjusted, setAdjusted] = useState(true);

  if (!api) {
    return (
      <Screen title="Libros">
        <NoSessionState />
      </Screen>
    );
  }

  return (
    <Screen title="Libros">
      <div className="px-5">
        {/* Cinco pestañas no caben en 362 px: la fila se desliza. */}
        <Segmented
          scroll
          value={tab}
          onChange={setTab}
          options={[
            { value: "resultados", label: "Resultados" },
            { value: "balance", label: "Balance" },
            { value: "diario", label: "Diario" },
            { value: "balanza", label: "Balanza" },
            { value: "indicadores", label: "Indicadores" },
          ]}
        />
      </div>
      <div className="mt-4">
        {tab === "resultados" && <IncomeTab period={period} setPeriod={setPeriod} adjusted={adjusted} />}
        {tab === "balance" && <BalanceTab adjusted={adjusted} />}
        {tab === "diario" && <JournalTab />}
        {tab === "balanza" && <TrialBalanceTab adjusted={adjusted} setAdjusted={setAdjusted} />}
        {tab === "indicadores" && <RatiosTab period={period} setPeriod={setPeriod} />}
      </div>
    </Screen>
  );
}

function Row({ row, negative }: { row: StatementRow; negative?: boolean }) {
  return (
    <li className="flex justify-between px-4 py-2 text-sm">
      <span className="text-muted">
        <span className="mr-2 text-[11px] tabular-nums">{row.account_number}</span>
        {row.account_name}
      </span>
      <span className="tabular-nums">
        {negative ? "−" : ""}
        {formatMoney(row.amount)}
      </span>
    </li>
  );
}

function TotalRow({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <li className={`flex justify-between border-t border-black/5 px-4 py-2 text-sm ${strong ? "font-semibold" : "font-medium"}`}>
      <span>{label}</span>
      <span className={`tabular-nums ${value < 0 ? "text-accent" : ""}`}>{formatMoney(value)}</span>
    </li>
  );
}

function IncomeTab({ period, setPeriod, adjusted }: { period: PeriodOpt; setPeriod: (p: PeriodOpt) => void; adjusted: boolean }) {
  const q = useBusinessQuery((a) => a.incomeStatement(period, adjusted), [period, adjusted]);
  return (
    <div className="px-5">
      <Segmented value={period} onChange={setPeriod} options={PERIODS} />
      {q.loading && !q.data && <LoadingState />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && (
        <Card className="mt-3 !px-0">
          <p className="px-4 pb-2 text-xs text-muted">
            Estado de resultados · {q.data.start ? `${formatDate(q.data.start)} – ${formatDate(q.data.end)}` : "desde el inicio"}
          </p>
          <ul>
            <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Ingresos</li>
            {q.data.revenue.map((r) => (
              <Row key={r.account_id} row={r} />
            ))}
            <TotalRow label="Total de ventas" value={q.data.total_revenue} />
            <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Costo de lo vendido</li>
            {q.data.cogs.map((r) => (
              <Row key={r.account_id} row={r} negative />
            ))}
            <TotalRow label="Utilidad bruta" value={q.data.gross_profit} strong />
            <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Gastos de operación</li>
            {q.data.operating_expenses.map((r) => (
              <Row key={r.account_id} row={r} negative />
            ))}
            <TotalRow label="Total de gastos" value={q.data.total_operating_expenses} />
            <TotalRow label="Utilidad neta" value={q.data.net_income} strong />
          </ul>
        </Card>
      )}
    </div>
  );
}

function BalanceTab({ adjusted }: { adjusted: boolean }) {
  const q = useBusinessQuery((a) => a.balanceSheet(adjusted), [adjusted]);
  return (
    <div className="px-5">
      {q.loading && !q.data && <LoadingState />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && (
        <>
          <div className="mb-3">
            {q.data.balanced ? <Notice tone="success">Cuadra: Activos = Pasivos + Capital.</Notice> : <ErrorState error={{ ok: false, kind: "unexpected", message: `El balance NO cuadra (diferencia ${formatMoney(q.data.difference)}). Es un error de integridad; no se oculta.` }} />}
          </div>
          <Card className="!px-0">
            <ul>
              <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Activos (lo que tienes)</li>
              {q.data.assets.map((r) => (
                <Row key={r.account_id} row={r} negative={r.normal_balance === "CREDIT"} />
              ))}
              <TotalRow label="Total activos" value={q.data.total_assets} strong />
              <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Pasivos (lo que debes)</li>
              {q.data.liabilities.map((r) => (
                <Row key={r.account_id} row={r} />
              ))}
              <TotalRow label="Total pasivos" value={q.data.total_liabilities} strong />
              <li className="px-4 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">Capital (lo que es tuyo)</li>
              {q.data.equity.map((r) => (
                <Row key={r.account_id} row={r} negative={r.normal_balance === "DEBIT"} />
              ))}
              <li className="flex justify-between px-4 py-2 text-sm">
                <span className="text-muted">Utilidad acumulada</span>
                <span className="tabular-nums">{formatMoney(q.data.current_earnings)}</span>
              </li>
              <TotalRow label="Total capital" value={q.data.total_equity} strong />
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}

function JournalTab() {
  const q = useBusinessQuery((a) => a.journal(80));
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="px-5">
      {q.loading && !q.data && <LoadingState />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && q.data.length === 0 && <p className="text-sm text-muted">Todavía no hay asientos.</p>}
      <ul className="space-y-2">
        {(q.data ?? []).map((e: JournalEntry) => (
          <li key={e.entry_id} className="rounded-2xl bg-white ring-1 ring-black/5">
            <button type="button" onClick={() => setOpen(open === e.entry_id ? null : e.entry_id)} aria-expanded={open === e.entry_id} className="flex w-full items-center gap-3 px-4 py-3 text-left">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{e.description}</p>
                <p className="text-[11px] text-muted">
                  JE-{String(e.transaction_number).padStart(5, "0")} · {formatDate(e.entry_date)} · {SOURCE_LABELS[e.source_type] ?? e.source_type}
                  {e.is_adjusting && " · ajuste"}
                </p>
              </div>
              <span className="text-sm font-semibold tabular-nums">{formatMoney(e.total_debit)}</span>
              <ChevronDown size={16} className={`text-muted transition-transform ${open === e.entry_id ? "rotate-180" : ""}`} aria-hidden />
            </button>
            {open === e.entry_id && (
              <table className="w-full border-t border-black/5 text-xs">
                <thead>
                  <tr className="text-muted">
                    <th className="px-4 py-1 text-left font-medium">Cuenta</th>
                    <th className="px-2 py-1 text-right font-medium">Debe</th>
                    <th className="px-4 py-1 text-right font-medium">Haber</th>
                  </tr>
                </thead>
                <tbody>
                  {e.lines.map((l) => (
                    <tr key={l.line_id}>
                      <td className={`px-4 py-1 ${l.credit > 0 ? "pl-8" : ""}`}>
                        {l.account_number} {l.account_name}
                        {l.memo && <span className="block text-[10px] text-muted">{l.memo}</span>}
                      </td>
                      <td className="px-2 py-1 text-right tabular-nums">{l.debit > 0 ? formatMoney(l.debit) : ""}</td>
                      <td className="px-4 py-1 text-right tabular-nums">{l.credit > 0 ? formatMoney(l.credit) : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TrialBalanceTab({ adjusted, setAdjusted }: { adjusted: boolean; setAdjusted: (v: boolean) => void }) {
  const q = useBusinessQuery((a) => a.trialBalance(adjusted), [adjusted]);
  return (
    <div className="px-5">
      <Segmented
        value={adjusted ? "adj" : "unadj"}
        onChange={(v) => setAdjusted(v === "adj")}
        options={[
          { value: "unadj", label: "Sin ajustes" },
          { value: "adj", label: "Ajustada" },
        ]}
      />
      {q.loading && !q.data && <LoadingState />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && (
        <Card className="mt-3 !px-0">
          <div className="flex items-center justify-between px-4 pb-2">
            <p className="text-xs text-muted">Balanza de comprobación</p>
            <StatusPill status={q.data.balanced ? "good" : "critical"} label={q.data.balanced ? "Cuadra" : "No cuadra"} />
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted">
                <th className="px-4 py-1 text-left font-medium">Cuenta</th>
                <th className="px-2 py-1 text-right font-medium">Debe</th>
                <th className="px-4 py-1 text-right font-medium">Haber</th>
              </tr>
            </thead>
            <tbody>
              {q.data.rows.map((r) => (
                <tr key={r.account_id} className="border-t border-black/5">
                  <td className="px-4 py-1.5">
                    <span className="mr-1 tabular-nums text-muted">{r.account_number}</span>
                    {r.account_name}
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{r.debit_balance > 0 ? formatMoney(r.debit_balance) : ""}</td>
                  <td className="px-4 py-1.5 text-right tabular-nums">{r.credit_balance > 0 ? formatMoney(r.credit_balance) : ""}</td>
                </tr>
              ))}
              <tr className="border-t border-black/10 font-semibold">
                <td className="px-4 py-2">Totales</td>
                <td className="px-2 py-2 text-right tabular-nums">{formatMoney(q.data.total_debit)}</td>
                <td className="px-4 py-2 text-right tabular-nums">{formatMoney(q.data.total_credit)}</td>
              </tr>
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

/** Las razones financieras explicadas, agrupadas por pregunta de negocio. */
function RatiosTab({ period, setPeriod }: { period: PeriodOpt; setPeriod: (p: PeriodOpt) => void }) {
  const q = useBusinessQuery((a) => a.ratios(period), [period]);
  return (
    <div className="px-5">
      <Segmented value={period} onChange={setPeriod} options={PERIODS} />
      {q.loading && !q.data && <LoadingState label="Calculando con tus libros…" />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && (
        <div className="mt-3 space-y-4" data-testid="ratios">
          <p className="text-xs text-muted">Indicadores {q.data.period.label}. Toca uno para ver cómo se calcula con tus cifras.</p>
          {GROUPS.map((g) => (
            <div key={g.key}>
              <p className="mb-2 text-xs font-semibold">{g.label}</p>
              <ul className="space-y-2">
                {q.data!.ratios
                  .filter((r) => r.group === g.key)
                  .map((r) => (
                    <RatioRow key={r.key} ratio={r} />
                  ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RatioRow({ ratio }: { ratio: Ratio }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-2xl bg-white ring-1 ring-black/5">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-center gap-3 px-4 py-3 text-left">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{ratio.label}</p>
          <p className="text-xs text-muted">{ratio.available ? ratio.explanation : `Aún no aplica: ${ratio.reason}.`}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-sm font-semibold tabular-nums">{ratioValue(ratio.value, ratio.unit)}</span>
          <StatusPill status={ratio.status} />
        </div>
        <ChevronDown size={16} className={`shrink-0 text-muted transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {open && (
        <div className="border-t border-black/5 px-4 py-3 text-xs text-muted">
          <p>
            <span className="font-semibold text-ink">Cómo se calcula:</span> {ratio.formula}
          </p>
          {Object.keys(ratio.inputs).length > 0 && (
            <p className="mt-1">
              {Object.entries(ratio.inputs)
                .map(([k, v]) => `${k.replace(/_/g, " ")}: ${typeof v === "number" && k !== "days" ? formatMoney(v) : v}`)
                .join(" · ")}
            </p>
          )}
          <Link to="/educacion" className="mt-2 inline-block font-semibold text-brand">
            Aprender qué significa
          </Link>
        </div>
      )}
    </li>
  );
}
