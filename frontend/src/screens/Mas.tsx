import {
  Bell,
  ChevronRight,
  CreditCard,
  HelpCircle,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Screen from "../components/Screen";
import { user } from "../data/mock";

const options: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "cards", label: "Mis tarjetas", icon: CreditCard },
  { id: "security", label: "Seguridad", icon: ShieldCheck },
  { id: "notifications", label: "Notificaciones", icon: Bell },
  { id: "settings", label: "Configuración", icon: Settings },
  { id: "help", label: "Ayuda", icon: HelpCircle },
];

export default function Mas() {
  return (
    <Screen title="Más">
      <section className="px-5">
        <div className="mb-6 flex items-center gap-3 rounded-2xl bg-white px-4 py-4">
          <span className="flex size-12 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold text-brand">
            {user.firstName[0]}
            {user.lastName[0]}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {user.firstName} {user.lastName}
            </p>
            <p className="text-xs text-muted">Cuenta personal</p>
          </div>
        </div>

        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
          {options.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                type="button"
                className="flex w-full items-center gap-3 px-4 py-3.5 text-left"
              >
                <Icon size={18} className="shrink-0 text-ink/70" aria-hidden />
                <span className="flex-1 text-sm font-medium">{label}</span>
                <ChevronRight size={16} className="text-muted" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </Screen>
  );
}
