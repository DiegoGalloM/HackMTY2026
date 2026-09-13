import { useNavigate } from "react-router-dom";
import {
  ArrowLeftRight,
  Banknote,
  Bell,
  BookOpen,
  ChevronRight,
  CreditCard,
  HandCoins,
  HelpCircle,
  MessageCircle,
  Package,
  Receipt,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Screen from "../components/Screen";
import { useBusiness } from "../business/BusinessContext";
import { user } from "../data/mock";

interface Option {
  id: string;
  label: string;
  caption?: string;
  icon: LucideIcon;
  to?: string;
}

const business: Option[] = [
  { id: "inventory", label: "Inventario", caption: "Existencias y movimientos", icon: Package, to: "/inventario" },
  { id: "purchases", label: "Compras con tarjeta", caption: "Clasificación y tickets", icon: CreditCard, to: "/compras" },
  { id: "assistant", label: "Asistente", caption: "Pregúntale a tu negocio", icon: MessageCircle, to: "/asistente" },
  { id: "books", label: "Libros", caption: "Resultados, balance, diario", icon: BookOpen, to: "/libros" },
];

const banking: Option[] = [
  { id: "cash", label: "Cobro en efectivo", icon: HandCoins, to: "/cobro-efectivo" },
  { id: "withdraw", label: "Retiros", icon: Banknote, to: "/retiros" },
  { id: "transfer", label: "Transferencias", icon: ArrowLeftRight, to: "/transferencias" },
  { id: "bills", label: "Pagos de servicios", icon: Receipt, to: "/pagos" },
];

const account: Option[] = [
  { id: "security", label: "Seguridad", icon: ShieldCheck },
  { id: "notifications", label: "Notificaciones", icon: Bell },
  { id: "settings", label: "Configuración", icon: Settings },
  { id: "help", label: "Ayuda", icon: HelpCircle },
];

export default function Mas() {
  const navigate = useNavigate();
  const { session, businessName } = useBusiness();
  const fullName = session?.user.full_name ?? `${user.firstName} ${user.lastName}`;
  const initials = fullName
    .split(" ")
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  const List = ({ title, options }: { title: string; options: Option[] }) => (
    <section className="mb-6 px-5">
      <h2 className="mb-2 text-sm font-semibold text-muted">{title}</h2>
      <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white">
        {options.map(({ id, label, caption, icon: Icon, to }) => (
          <li key={id}>
            <button
              type="button"
              onClick={() => to && navigate(to)}
              className="flex w-full items-center gap-3 px-4 py-3.5 text-left"
            >
              <Icon size={18} className="shrink-0 text-ink/70" aria-hidden />
              <span className="flex-1">
                <span className="block text-sm font-medium">{label}</span>
                {caption && <span className="block text-xs text-muted">{caption}</span>}
              </span>
              <ChevronRight size={16} className="text-muted" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );

  return (
    <Screen title="Más">
      <section className="px-5">
        <div className="mb-6 flex items-center gap-3 rounded-2xl bg-white px-4 py-4">
          <span className="flex size-12 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold text-brand">
            {initials}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{fullName}</p>
            <p className="truncate text-xs text-muted">{session ? businessName : "Cuenta personal"}</p>
          </div>
        </div>
      </section>
      <List title="Mi negocio" options={business} />
      <List title="Banca" options={banking} />
      <List title="Cuenta" options={account} />
    </Screen>
  );
}
