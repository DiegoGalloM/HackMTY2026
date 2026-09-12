import { MapPin } from "lucide-react";
import Screen from "../components/Screen";
import { atms, formatCurrency } from "../data/mock";

const amounts = [200, 500, 1000, 2000];

export default function Retiros() {
  return (
    <Screen title="Retiros">
      <section className="px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">
          Retiro sin tarjeta
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {amounts.map((amount) => (
            <button
              key={amount}
              type="button"
              className="rounded-2xl bg-tile py-6 text-lg font-semibold tabular-nums transition-transform active:scale-[0.97]"
            >
              {formatCurrency(amount)}
            </button>
          ))}
        </div>
      </section>

      <section className="mt-8 px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">Cajeros cerca</h2>
        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
          {atms.map((atm) => (
            <li key={atm.id} className="flex items-center gap-3 px-4 py-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-tile">
                <MapPin size={16} className="text-ink/70" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{atm.name}</p>
                <p className="text-xs text-muted">
                  {atm.distance} ·{" "}
                  {atm.fee === 0 ? "Sin comisión" : `Comisión ${formatCurrency(atm.fee)}`}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </Screen>
  );
}
