import { Plus } from "lucide-react";
import Screen from "../components/Screen";
import { contacts } from "../data/mock";

/** Iniciales para el avatar del contacto. */
function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function Transferencias() {
  return (
    <Screen title="Transferencias">
      <section className="px-5">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-2xl bg-brand px-4 py-4 text-left text-white transition-transform active:scale-[0.98]"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-white/20">
            <Plus size={18} aria-hidden />
          </span>
          <span>
            <span className="block text-sm font-semibold">Nueva transferencia</span>
            <span className="block text-xs text-white/75">
              CLABE, tarjeta o celular
            </span>
          </span>
        </button>
      </section>

      <section className="mt-8 px-5">
        <h2 className="mb-3 text-sm font-semibold text-muted">Contactos frecuentes</h2>
        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
          {contacts.map((contact) => (
            <li key={contact.id} className="flex items-center gap-3 px-4 py-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand/10 text-xs font-semibold text-brand">
                {initials(contact.name)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{contact.name}</p>
                <p className="text-xs text-muted tabular-nums">
                  {contact.bank} · •••• {contact.clabeLast4}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </Screen>
  );
}
