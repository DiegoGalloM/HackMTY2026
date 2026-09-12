import Screen from "../components/Screen";
import { formatCurrency, formatDate, services } from "../data/mock";

export default function Pagos() {
  return (
    <Screen title="Pagos">
      <section className="px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">
          Servicios por pagar
        </h2>
        <ul className="space-y-3">
          {services.map((service) => (
            <li
              key={service.id}
              className="flex items-center gap-3 rounded-2xl bg-white px-4 py-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{service.name}</p>
                <p className="text-xs text-muted">
                  {service.category} · vence {formatDate(service.dueDate)}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-semibold tabular-nums">
                  {formatCurrency(service.amount)}
                </p>
                <button
                  type="button"
                  className="mt-1 rounded-full bg-accent px-3 py-1 text-xs font-medium text-white transition-transform active:scale-95"
                >
                  Pagar
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </Screen>
  );
}
