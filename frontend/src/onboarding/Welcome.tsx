import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, ChartNoAxesCombined, Check, ChevronRight, Croissant, Scissors, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { DemoBusinessKey } from "../api/types";
import CreditCardTile from "../components/CreditCardTile";
import CapitalOneLogo from "../components/CapitalOneLogo";
import BottomSheet from "../components/BottomSheet";
import LoginForm from "../auth/LoginForm";
import RegisterForm from "../auth/RegisterForm";
import type { Session } from "../auth/session";
import type { LocalProfile } from "../business/BusinessContext";
import "./entry.css";

interface WelcomeProps {
  /** Se llama con la sesión ya creada por /auth/register o /auth/login. */
  onAuthenticated: (session: Session) => void | Promise<void>;
  /** Camino sin cuenta: la demo abierta con el negocio elegido. */
  onExplore: (business: DemoBusinessKey) => void;
}

interface DemoBusinessCard {
  key: DemoBusinessKey;
  name: string;
  place: string;
  category: NonNullable<LocalProfile["category"]>;
  categoryLabel: string;
  /** Qué demuestra este negocio, en una línea. */
  shows: string;
  icon: LucideIcon;
  /** Respuestas de la encuesta guardadas en el backend para este negocio
   * (deciden la lección de Cash Insight en Cuenta). Espejo de demo.py. */
  answers: LocalProfile["answers"];
}

/** Los negocios de ejemplo del backend (backend/app/finance/demo.py). */
export const DEMO_BUSINESSES: Record<DemoBusinessKey, DemoBusinessCard> = {
  panaderia: {
    key: "panaderia",
    name: "Panadería La Espiga",
    place: "Austin, TX",
    category: "comida",
    categoryLabel: "comida",
    shows: "Productos con receta, inventario perecedero y compras al mayoreo con ticket.",
    icon: Croissant,
    answers: { guarda_inventario: true, se_ha_quedado_sin_stock: true, compra_mayoreo: true },
  },
  estetica: {
    key: "estetica",
    name: "Estética Carolina",
    place: "Monterrey, MX",
    category: "belleza",
    categoryLabel: "belleza",
    shows: "Servicios que consumen insumos, venta de producto y cifras en pesos.",
    icon: Scissors,
    answers: { vende_producto_fisico: true, guarda_inventario: false, compra_mayoreo: false, se_ha_quedado_sin_stock: false, compro_de_mas: false, vende_en_local_fijo: true, usa_insumos_belleza: true, vende_retail: true },
  },
};

const steps = ["Cuéntanos de ti", "Construye tu perfil", "Da el siguiente paso"];

/**
 * Hero de bienvenida, pensado para la pantalla del mockup de celular
 * (.phone-frame__screen, ~362px útiles en desktop y 100% del ancho en móvil).
 * La propia página es el contenedor de scroll: el marco no scrollea.
 */
export default function Welcome({ onAuthenticated, onExplore }: WelcomeProps) {
  const [mode, setMode] = useState<"welcome" | "register" | "login">("welcome");
  const [picking, setPicking] = useState(false);
  const page = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const previousMode = useRef(mode);

  useEffect(() => {
    // Solo al cambiar de modo: en la carga inicial el foco no se mueve. Se
    // compara contra el modo anterior (y no con un flag de "ya montó") porque
    // StrictMode corre el efecto dos veces al montar.
    if (previousMode.current === mode) return;
    previousMode.current = mode;
    page.current?.scrollTo({ top: 0 });
    heading.current?.focus({ preventScroll: true });
  }, [mode]);

  const isWelcome = mode === "welcome";

  return (
    <div className="entry-page" ref={page}>
      <header className="entry-header">
        <button className="entry-brand" aria-label="Capital One Business, inicio" onClick={() => setMode("welcome")}>
          <CapitalOneLogo business className="text-[20px] text-navy" />
        </button>
        <div className="entry-header-actions">
          <span className="entry-demo">Demo</span>
          {isWelcome
            ? <button className="entry-login" onClick={() => setMode("login")}>Iniciar sesión <ArrowRight size={14} aria-hidden /></button>
            : <button className="entry-login" aria-label="Volver al inicio" onClick={() => setMode("welcome")}><ArrowLeft size={14} aria-hidden /> Volver</button>}
        </div>
      </header>

      <main className={`entry-main${isWelcome ? "" : " entry-main--access"}`}>
        <section className="entry-visual" aria-label="Tu tarjeta de negocio">
          <div className="entry-orbit entry-orbit--outer" aria-hidden />
          <div className="entry-orbit entry-orbit--inner" aria-hidden />
          <div className="entry-card"><CreditCardTile artwork="demo" /></div>
          {isWelcome && (
            <div className="entry-floating-note">
              <span className="entry-note-icon"><ChartNoAxesCombined size={18} aria-hidden /></span>
              <div><strong>Grandes planes.</strong><span>Empiezan con tu negocio.</span></div>
              <span className="entry-note-check"><Check size={12} aria-hidden /></span>
            </div>
          )}
        </section>

        <section className="entry-copy" aria-labelledby="entry-title" key={mode}>
          {isWelcome ? (
            <>
              <p className="entry-eyebrow"><span /> PARA QUIENES MUEVEN EL MUNDO</p>
              <h1 id="entry-title" ref={heading} tabIndex={-1}>Tu negocio<br /><em>en tus manos</em></h1>
              <p className="entry-description">Una nueva forma de entender tu dinero y hacer crecer lo que estás construyendo. Empecemos por conocerte.</p>
              <div className="entry-actions">
                <button className="entry-primary" onClick={() => setMode("register")}>Registrarme <ArrowRight size={18} aria-hidden /></button>
                <button className="entry-secondary" onClick={() => setMode("login")}>Ya tengo una cuenta</button>
              </div>
            </>
          ) : (
            <>
              <p className="entry-eyebrow"><span /> TU PRÓXIMO CAPÍTULO EMPIEZA AQUÍ</p>
              <h1 id="entry-title" ref={heading} tabIndex={-1}>{mode === "register" ? "Dale un espacio a tu negocio." : "Qué bueno verte de nuevo."}</h1>
              <p className="entry-description">{mode === "register" ? "Crea tu perfil y cuéntanos un poco sobre tu negocio para personalizar tu experiencia." : "Entra a la experiencia y comienza a construir el perfil de tu negocio."}</p>
              {mode === "register" ? (
                <>
                  <div className="entry-demo-note"><Sparkles size={18} aria-hidden /><p><strong>Estás en la versión de demostración.</strong><br />Tu cuenta y tus respuestas se guardan solo en el backend de esta demo.</p></div>
                  <RegisterForm onAuthenticated={onAuthenticated} onSwitchToLogin={() => setMode("login")} />
                </>
              ) : (
                <LoginForm onAuthenticated={onAuthenticated} onSwitchToRegister={() => setMode("register")} />
              )}
            </>
          )}
        </section>
      </main>

      <footer className="entry-footer">
        <ol aria-label="Cómo funciona">
          {steps.map((label, index) => <li key={label}><span>0{index + 1}</span>{label}</li>)}
        </ol>
        <button onClick={() => setPicking(true)}>Explorar la demo <ArrowRight size={14} aria-hidden /></button>
      </footer>

      {/* Un toque más: elegir qué negocio de ejemplo explorar. */}
      <AnimatePresence>
        {picking && (
          <BottomSheet label="Elige un negocio de ejemplo" onDismiss={() => setPicking(false)}>
            <h2 className="mt-3 text-lg font-semibold tracking-tight text-ink">¿Qué negocio quieres explorar?</h2>
            <p className="mt-1 text-xs text-muted">Los dos usan el mismo motor: otro giro, otro país y otro catálogo de cuentas.</p>
            <ul className="mt-4 space-y-2">
              {Object.values(DEMO_BUSINESSES).map((b) => {
                const Icon = b.icon;
                return (
                  <li key={b.key}>
                    <button
                      type="button"
                      onClick={() => { setPicking(false); onExplore(b.key); }}
                      className="flex w-full items-center gap-3 rounded-2xl bg-surface px-4 py-3 text-left ring-1 ring-black/5"
                    >
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand"><Icon size={20} aria-hidden /></span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold text-ink">{b.name}</span>
                        <span className="block text-[11px] text-muted">{b.place} · {b.categoryLabel}</span>
                        <span className="mt-1 block text-xs text-ink/80">{b.shows}</span>
                      </span>
                      <ChevronRight size={16} className="shrink-0 text-muted" aria-hidden />
                    </button>
                  </li>
                );
              })}
            </ul>
          </BottomSheet>
        )}
      </AnimatePresence>
    </div>
  );
}
