import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, ChartNoAxesCombined, Check, Clock3, Sparkles } from "lucide-react";
import CreditCardTile from "../components/CreditCardTile";
import CapitalOneLogo from "../components/CapitalOneLogo";
import LoginForm from "../auth/LoginForm";
import RegisterForm from "../auth/RegisterForm";
import type { Session } from "../auth/session";
import "./entry.css";

interface WelcomeProps {
  /** Se llama con la sesión ya creada por /auth/register o /auth/login. */
  onAuthenticated: (session: Session) => void;
  /** Camino sin cuenta: la demo abierta, que no toca endpoints protegidos. */
  onExplore: () => void;
}

const steps = ["Cuéntanos de ti", "Construye tu perfil", "Da el siguiente paso"];

/**
 * Hero de bienvenida, pensado para la pantalla del mockup de celular
 * (.phone-frame__screen, ~362px útiles en desktop y 100% del ancho en móvil).
 * La propia página es el contenedor de scroll: el marco no scrollea.
 */
export default function Welcome({ onAuthenticated, onExplore }: WelcomeProps) {
  const [mode, setMode] = useState<"welcome" | "register" | "login">("welcome");
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
          {isWelcome && <span className="entry-visual-caption">HECHA PARA TU SIGUIENTE PASO</span>}
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
              <h1 id="entry-title" ref={heading} tabIndex={-1}>Tu negocio.<br />Tu esfuerzo.<br /><em>Tu siguiente paso.</em></h1>
              <p className="entry-description">Una nueva forma de entender tu dinero y hacer crecer lo que estás construyendo. Empecemos por conocerte.</p>
              <div className="entry-actions">
                <button className="entry-primary" onClick={() => setMode("register")}>Registrarme <ArrowRight size={18} aria-hidden /></button>
                <button className="entry-secondary" onClick={() => setMode("login")}>Ya tengo una cuenta</button>
                <p className="entry-time"><Clock3 size={14} aria-hidden /> Una breve encuesta. Un espacio a tu medida.</p>
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
        <button onClick={onExplore}>Explorar la demo <ArrowRight size={14} aria-hidden /></button>
      </footer>
    </div>
  );
}
