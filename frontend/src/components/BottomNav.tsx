import { NavLink } from "react-router-dom";
import { ChartColumn, CreditCard, Landmark, LayoutGrid, QrCode } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { DEMO_BADGE } from "./DemoNotice";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** El botón central va elevado, sobresaliendo por encima de la barra. */
  raised?: boolean;
}

// Vender y Compras son el día a día del dueño (entra dinero, sale dinero);
// Análisis al centro es donde todo eso se vuelve inteligencia. Retiros,
// transferencias y pagos de servicios siguen disponibles desde "Más".
const items: NavItem[] = [
  { to: "/", label: "Cuenta", icon: Landmark },
  { to: "/vender", label: "Vender", icon: QrCode },
  {
    to: "/analisis",
    label: "Análisis",
    icon: ChartColumn,
    raised: true,
  },
  { to: "/compras", label: "Compras", icon: CreditCard },
  { to: "/mas", label: "Más", icon: LayoutGrid },
];

export default function BottomNav() {
  return (
    <nav
      aria-label="Navegación principal"
      // absolute (no fixed) para quedarse dentro del shell de la app, que vive
      // dentro del mockup de celular; el efecto en móvil es el mismo.
      // pb con env(safe-area-inset-bottom) para que la home indicator de iOS
      // no se encime con los íconos.
      className="absolute inset-x-0 bottom-0 z-20 border-t border-black/5 bg-white/95 backdrop-blur-md pb-[var(--safe-bottom)]"
    >
      <ul className="flex h-[var(--nav-height)] items-center justify-around px-2">
        {items.map(({ to, label, icon: Icon, raised }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={to === "/"}
              className="group flex flex-col items-center gap-1 outline-none"
            >
              {({ isActive }) =>
                raised ? (
                  <>
                    <span
                      className={`-mt-8 flex size-14 items-center justify-center rounded-full text-white shadow-lg ring-4 ring-white transition-transform group-active:scale-95 ${
                        isActive
                          ? "bg-brand shadow-brand/40"
                          : "bg-brand/90 shadow-brand/25"
                      }`}
                    >
                      <Icon size={22} aria-hidden />
                    </span>
                    <span
                      className={`text-[10px] leading-none font-medium ${
                        isActive ? "text-brand" : "text-muted"
                      }`}
                    >
                      {label}
                    </span>
                  </>
                ) : (
                  <>
                    <Icon
                      size={20}
                      aria-hidden
                      className={isActive ? "text-brand" : "text-muted"}
                    />
                    <span
                      className={`text-[10px] leading-none ${
                        isActive ? "font-medium text-brand" : "text-muted"
                      }`}
                    >
                      {label}
                    </span>
                  </>
                )
              }
            </NavLink>
          </li>
        ))}
      </ul>
      {/* Franja persistente: va en la barra, así se ve en TODAS las pantallas de
          la app y quien la prueba nunca pierde de vista que es una simulación.
          Debajo de los íconos y no encima, porque el botón central sobresale
          por arriba y la taparía. Su alto se reserva en Screen.tsx. */}
      <p
        role="note"
        className="flex h-[var(--demo-band-height)] items-center justify-center bg-navy text-[10px] font-semibold tracking-[0.08em] text-white uppercase"
      >
        {DEMO_BADGE}
      </p>
    </nav>
  );
}
