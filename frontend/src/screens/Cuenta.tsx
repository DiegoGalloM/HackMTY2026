import BalanceHeader from "../components/BalanceHeader";
import CreditCardTile from "../components/CreditCardTile";
import QuickActionsGrid from "../components/QuickActionsGrid";
import Screen from "../components/Screen";
import { formatCurrency, formatDate, movements } from "../data/mock";

export default function Cuenta() {
  return (
    <Screen>
      <BalanceHeader />
      <CreditCardTile />

      <div className="mt-6">
        <QuickActionsGrid />
      </div>

      <section className="mt-8 px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">
          Últimos movimientos
        </h2>
        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
          {movements.map((m) => (
            <li key={m.id} className="flex items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{m.title}</p>
                <p className="text-xs text-muted">
                  {m.category} · {formatDate(m.date)}
                </p>
              </div>
              <span
                className={`shrink-0 text-sm font-semibold tabular-nums ${
                  m.amount > 0 ? "text-positive" : "text-ink"
                }`}
              >
                {m.amount > 0 ? "+" : ""}
                {formatCurrency(m.amount)}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </Screen>
  );
}
