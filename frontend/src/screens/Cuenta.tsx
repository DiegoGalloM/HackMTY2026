import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { formatDateTime, formatMoney } from "../api/format";
import BalanceHeader from "../components/BalanceHeader";
import CreditCardTile from "../components/CreditCardTile";
import QuickActionsGrid from "../components/QuickActionsGrid";
import Screen from "../components/Screen";
import { StatusPill } from "../components/ui";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import { formatDate, movements } from "../data/mock";

interface CuentaProps {
  profile: {
    category: string | null;
    answers: Record<string, boolean>;
    name?: string;
    lastName?: string;
  } | null;
}

interface Movement {
  id: string;
  title: string;
  caption: string;
  amount: number;
  at: string;
}

export default function Cuenta({ profile }: CuentaProps) {
  const { api, businessName } = useBusiness();
  const overview = useBusinessQuery((a) => a.overview());

  // El saludo se queda con el PRIMER nombre aunque la persona haya escrito
  // dos: "Hola Carlos!" y no "Hola Carlos Alberto!".
  // "Usuario" cubre los dos casos sin nombre: encuesta saltada desde el primer
  // paso, o perfil viejo guardado antes de que existiera la pregunta.
  const firstName = profile?.name?.trim().split(" ")[0] || "Usuario";

  // La tarjeta sí lleva el nombre completo, como el plástico de verdad, y en
  // mayúsculas como viene impreso. Sin nombre dice USUARIO, igual que el
  // saludo de arriba.
  const fullName = [profile?.name, profile?.lastName]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(" ");
  const holder = fullName ? fullName.toUpperCase() : "USUARIO";

  const h = overview.data?.health;

  // Últimos movimientos reales: ventas pagadas por QR y compras con la
  // tarjeta, mezclados por fecha. Sin sesión se muestran los de demo.
  const recent: Movement[] = overview.data
    ? [
        ...overview.data.recent_orders.map((o) => ({
          id: o.order_id,
          title: `Venta #${o.order_number} · ${o.lines.map((l) => `${l.quantity} ${l.item_name}`).join(", ")}`,
          caption: "Cobro con QR",
          amount: o.total,
          at: o.paid_at ?? o.created_at,
        })),
        ...overview.data.recent_purchases.map((t) => ({
          id: t.transaction_id,
          title: t.merchant,
          caption: t.kind_label ?? "Tarjeta de negocio",
          amount: t.direction === "CREDIT" ? t.amount : -t.amount,
          at: t.occurred_at,
        })),
      ]
        .sort((a, b) => (a.at < b.at ? 1 : -1))
        .slice(0, 8)
    : [];

  return (
    <Screen>
      <BalanceHeader firstName={firstName} balance={h ? h.cash.cash_available : null} label={api ? `Efectivo de ${businessName}` : undefined} />
      <CreditCardTile flippable holder={holder} />

      <div className="mt-6">
        <QuickActionsGrid />
      </div>

      {h && (
        <section className="mt-6 px-5">
          <Link to="/analisis" className="block rounded-2xl bg-white px-4 py-4 ring-1 ring-black/5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">Cómo va el negocio {h.period.label}</p>
              <ChevronRight size={16} className="text-muted" aria-hidden />
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-[11px] text-muted">Ventas</p>
                <p className="text-sm font-semibold tabular-nums">{formatMoney(h.revenue.value)}</p>
              </div>
              <div>
                <p className="text-[11px] text-muted">Ganancia</p>
                <p className={`text-sm font-semibold tabular-nums ${h.net_income.value < 0 ? "text-accent" : "text-positive"}`}>{formatMoney(h.net_income.value)}</p>
              </div>
              <div>
                <p className="text-[11px] text-muted">Caja</p>
                <StatusPill status={h.cash.status} />
              </div>
            </div>
            {h.attention[0] && <p className="mt-3 text-xs text-muted">⚡ {h.attention[0].title}</p>}
          </Link>
        </section>
      )}

      <section className="mt-8 px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">
          Últimos movimientos
        </h2>
        {api && overview.error && (
          <p className="mb-3 text-xs text-accent" role="alert">
            {overview.error.message}
          </p>
        )}
        {api && overview.data && recent.length === 0 && <p className="text-xs text-muted">Todavía no hay movimientos. Cobra con QR o usa tu tarjeta de negocio y aparecerán aquí.</p>}
        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
          {api
            ? recent.map((m) => (
                <li key={m.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{m.title}</p>
                    <p className="text-xs text-muted">
                      {m.caption} · {formatDateTime(m.at)}
                    </p>
                  </div>
                  <span className={`shrink-0 text-sm font-semibold tabular-nums ${m.amount > 0 ? "text-positive" : "text-ink"}`}>
                    {m.amount > 0 ? "+" : ""}
                    {formatMoney(m.amount)}
                  </span>
                </li>
              ))
            : movements.map((m) => (
                <li key={m.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{m.title}</p>
                    <p className="text-xs text-muted">
                      {m.category} · {formatDate(m.date)}
                    </p>
                  </div>
                  <span className={`shrink-0 text-sm font-semibold tabular-nums ${m.amount > 0 ? "text-positive" : "text-ink"}`}>
                    {m.amount > 0 ? "+" : ""}
                    {formatMoney(m.amount)}
                  </span>
                </li>
              ))}
        </ul>
      </section>
    </Screen>
  );
}
