import { useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, ChevronDown, MessageCircle, TrendingDown, TrendingUp } from "lucide-react";
import { formatChange, formatMoney, ratioValue } from "../api/format";
import type { Ratio } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import { Card, EmptyState, ErrorState, LoadingState, NoSessionState, Notice, SectionTitle, Segmented, StatusPill } from "../components/ui";

type PeriodOpt = "week" | "month" | "30d";
const GROUPS: { key: Ratio["group"]; label: string }[] = [
  { key: "liquidez", label: "Liquidez: ¿puedes pagar lo que debes pronto?" },
  { key: "rentabilidad", label: "Rentabilidad: ¿te queda ganancia?" },
  { key: "eficiencia", label: "Inventario: ¿tu dinero se mueve?" },
  { key: "apalancamiento", label: "Deuda: ¿de quién es el negocio?" },
];

/**
 * Análisis financiero. Primero lo que importa (ventas, ganancia, caja,
 * inventario) en lenguaje llano; las razones y los libros formales quedan
 * un nivel abajo para quien quiera verlos. Todos los números vienen del
 * backend, derivados del diario.
 */
export default function Analisis() {
  const { api, businessName } = useBusiness();
  const [period, setPeriod] = useState<PeriodOpt>("month");
  const health = useBusinessQuery((a) => a.health(period), [period]);

  if (!api) {
    return (
      <Screen title="Análisis Financiero">
        <NoSessionState />
      </Screen>
    );
  }

  const h = health.data;

  return (
    <Screen title="Análisis Financiero">
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

          <section className="mt-6 px-5">
            <SectionTitle>Tus indicadores, explicados</SectionTitle>
            <div className="space-y-4">
              {GROUPS.map((g) => (
                <div key={g.key}>
                  <p className="mb-2 text-xs font-semibold">{g.label}</p>
                  <ul className="space-y-2">
                    {h.ratios
                      .filter((r) => r.group === g.key)
                      .map((r) => (
                        <RatioRow key={r.key} ratio={r} />
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6 px-5">
            <div className="grid grid-cols-2 gap-2">
              <Link to="/libros" className="flex min-h-11 items-center justify-center gap-2 rounded-full bg-tile text-sm font-semibold">
                <BookOpen size={16} aria-hidden /> Ver mis libros
              </Link>
              <Link to="/asistente" className="flex min-h-11 items-center justify-center gap-2 rounded-full bg-brand text-sm font-semibold text-white">
                <MessageCircle size={16} aria-hidden /> Preguntar
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
