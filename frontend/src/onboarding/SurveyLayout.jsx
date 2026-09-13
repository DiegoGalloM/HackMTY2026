import { useEffect, useRef } from "react";
import { ArrowLeft, Check, Sparkles } from "lucide-react";
import CapitalOneLogo from "../components/CapitalOneLogo";
import "./entry.css";

const sections = [
  ["Tu negocio", "Lo que haces y cómo trabajas"],
  ["Tu día a día", "Tu semana y tu equipo"],
  ["Tu perfil", "Los últimos detalles"],
];

export default function SurveyLayout({ children, section, progress, stepKey, title, description, kicker, onExit, busy, active }) {
  const titleRef = useRef(null);
  const pageRef = useRef(null);

  useEffect(() => {
    if (!active) return;
    // La página es el contenedor de scroll dentro del mockup: cada paso
    // arranca arriba en vez de heredar el scroll del anterior.
    pageRef.current?.scrollTo({ top: 0 });
    titleRef.current?.focus({ preventScroll: true });
  }, [stepKey, active]);

  return (
    <main className="survey-page" ref={pageRef}>
      <header className="survey-header">
        <CapitalOneLogo business className="text-[25px] text-navy" />
        <button className="entry-back" onClick={onExit} disabled={busy}><ArrowLeft size={16} aria-hidden /> Ir al inicio</button>
      </header>
      <div className="survey-layout">
        <aside className="survey-aside" aria-label="Etapas de tu perfil">
          <p className="entry-eyebrow">UN ESPACIO A TU MEDIDA</p>
          <h2>Cada negocio<br />tiene su historia.</h2>
          <p>Cuéntanos la tuya. Tus respuestas nos ayudan a entender qué necesita tu negocio.</p>
          <ol className="survey-steps">
            {sections.map(([label, detail], index) => (
              <li key={label} aria-current={section === index ? "step" : undefined} className={section > index ? "is-complete" : ""}>
                <span>{section > index ? <Check size={14} aria-hidden /> : `0${index + 1}`}</span>
                <div><strong>{label}</strong><small>{detail}</small></div>
              </li>
            ))}
          </ol>
          <div className="survey-aside-note"><Sparkles size={17} aria-hidden /><span>No hay respuestas correctas o incorrectas. Solo la forma en que tú haces las cosas.</span></div>
        </aside>
        <section className="survey-panel" aria-labelledby="survey-title" aria-busy={busy}>
          <div className="survey-progress-label"><span>Tu perfil de negocio</span><span>{Math.round(progress * 100)}%</span></div>
          <div className="survey-progress" role="progressbar" aria-label="Progreso de la encuesta" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}><div style={{ width: `${progress * 100}%` }} /></div>
          <div className="survey-step-body" key={stepKey}>
            <p className="survey-kicker">{kicker}</p>
            <h1 id="survey-title" ref={titleRef} tabIndex={-1}>{title}</h1>
            <p className="survey-description">{description}</p>
            {children}
          </div>
        </section>
      </div>
    </main>
  );
}
