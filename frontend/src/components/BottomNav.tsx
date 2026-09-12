import { NavLink } from "react-router-dom";
import { ArrowLeftRight, Banknote, LayoutGrid, Landmark, Receipt } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** El botón central va elevado, sobresaliendo por encima de la barra. */
  raised?: boolean;
}

const items: NavItem[] = [
  { to: "/", label: "Cuenta", icon: Landmark },
  { to: "/retiros", label: "Retiros", icon: Banknote },
  {
    to: "/transferencias",
    label: "Transferencias",
    icon: ArrowLeftRight,
    raised: true,
  },
  { to: "/pagos", label: "Pagos", icon: Receipt },
  { to: "/mas", label: "Más", icon: LayoutGrid },
];

export default function BottomNav() {
  return (
    <nav
      aria-label="Navegación principal"
      // absolute (no fixed) para quedarse dentro del shell de max-w-md en
      // desktop; el shell mide 100dvh, así que el efecto en móvil es el mismo.
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
                          ? "bg-accent shadow-accent/40"
                          : "bg-accent/90 shadow-accent/25"
                      }`}
                    >
                      <Icon size={22} aria-hidden />
                    </span>
                    <span className="text-[10px] leading-none font-medium text-accent">
                      {label}
                    </span>
                  </>
                ) : (
                  <>
                    <Icon
                      size={20}
                      aria-hidden
                      className={isActive ? "text-accent" : "text-muted"}
                    />
                    <span
                      className={`text-[10px] leading-none ${
                        isActive ? "font-medium text-accent" : "text-muted"
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
    </nav>
  );
}
