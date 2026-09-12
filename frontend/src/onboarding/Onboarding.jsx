// frontend/src/onboarding/Onboarding.jsx
import { useCallback, useMemo, useState } from "react";
import { Bubble, BubbleGrid } from "./Bubble.jsx";
import { CATEGORIES, UNIVERSAL_QUESTIONS, CATEGORY_QUESTIONS, WEEKDAYS, EMPLOYEE_OPTIONS } from "./questions.js";

const API_BASE = "http://localhost:8000";
const STEPS = ["welcome", "questions", "schedule", "employees", "city", "done"];

export default function Onboarding({ ownerId = "demo-owner" }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [category, setCategory] = useState(null);
  const [answers, setAnswers] = useState({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [days, setDays] = useState([]);
  const [employees, setEmployees] = useState(null);
  const [city, setCity] = useState("");
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const step = STEPS[stepIndex];
  const questions = useMemo(() => {
    if (!category) return [];
    return [...UNIVERSAL_QUESTIONS, ...(CATEGORY_QUESTIONS[category] ?? [])];
  }, [category]);

  const goToStep = useCallback((name) => setStepIndex(STEPS.indexOf(name)), []);

  const pickCategory = (id) => { setCategory(id); setQuestionIndex(0); goToStep("questions"); };

  const answerQuestion = (value) => {
    const q = questions[questionIndex];
    setAnswers((prev) => ({ ...prev, [q.id]: value }));
    if (questionIndex + 1 < questions.length) setQuestionIndex((i) => i + 1);
    else goToStep("schedule");
  };

  const toggleDay = (id) => setDays((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));

  const detectCity = () => {
    setLocating(true); setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
          const data = await res.json();
          const detected = data.address?.city || data.address?.town || data.address?.village || data.address?.county;
          if (detected) setCity(detected); else setLocationError("No pudimos detectar tu ciudad, escríbela abajo.");
        } catch { setLocationError("No pudimos detectar tu ciudad, escríbela abajo."); }
        finally { setLocating(false); }
      },
      () => { setLocationError("Ubicación no disponible, escribe tu ciudad abajo."); setLocating(false); }
    );
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      await fetch(`${API_BASE}/business-profile/${ownerId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, operating_days: days, city, employees, answers }),
      });
      setSubmitted(true);
    } catch {
      setSubmitted(false);
    } finally {
      setSubmitting(false);
      goToStep("done");
    }
  };

  if (step === "welcome") return (
    <Screen transitionKey="welcome">
      <h1 className="ob-title">Bienvenido a Capital One Business:</h1>
      <p className="ob-subtitle">Selecciona tu modelo de negocio</p>
      <BubbleGrid>
        {CATEGORIES.map((c) => <Bubble key={c.id} label={c.label} icon={c.icon} size="large" onClick={() => pickCategory(c.id)} />)}
      </BubbleGrid>
    </Screen>
  );

  if (step === "questions") {
    const q = questions[questionIndex];
    return (
      <Screen transitionKey={`question-${questionIndex}`}>
        <ProgressBar value={(questionIndex + 1) / questions.length} />
        <p className="ob-question">{q.text}</p>
        <BubbleGrid>
          <Bubble label="No" variant="no" onClick={() => answerQuestion(false)} />
          <Bubble label="Sí" variant="yes" onClick={() => answerQuestion(true)} />
        </BubbleGrid>
      </Screen>
    );
  }

  if (step === "schedule") return (
    <Screen transitionKey="schedule">
      <p className="ob-subtitle">¿Qué días opera tu negocio?</p>
      <BubbleGrid>{WEEKDAYS.map((d) => <Bubble key={d.id} label={d.label} selected={days.includes(d.id)} onClick={() => toggleDay(d.id)} />)}</BubbleGrid>
      <button className="ob-continue" disabled={days.length === 0} onClick={() => goToStep("employees")}>Continuar</button>
    </Screen>
  );

  if (step === "employees") return (
    <Screen transitionKey="employees">
      <p className="ob-subtitle">¿Cuántas personas trabajan contigo?</p>
      <BubbleGrid>{EMPLOYEE_OPTIONS.map((e) => <Bubble key={e.id} label={e.label} selected={employees === e.id} onClick={() => { setEmployees(e.id); goToStep("city"); }} />)}</BubbleGrid>
    </Screen>
  );

  if (step === "city") return (
    <Screen transitionKey="city">
      <p className="ob-subtitle">¿En qué ciudad opera tu negocio?</p>
      <button className="ob-continue" onClick={detectCity} disabled={locating}>{locating ? "Buscando…" : "📍 Usar mi ubicación"}</button>
      {locationError && <p className="ob-error">{locationError}</p>}
      <input className="ob-input" placeholder="O escribe tu ciudad" value={city} onChange={(e) => setCity(e.target.value)} />
      <button className="ob-continue" disabled={!city} onClick={submit}>{submitting ? "Guardando…" : "Terminar"}</button>
    </Screen>
  );

  return (
    <Screen transitionKey="done">
      <h2 className="ob-title">{submitted ? "¡Listo! 🎉" : "Algo salió mal, intenta de nuevo."}</h2>
      <p className="ob-subtitle">Tu perfil de negocio quedó guardado.</p>
    </Screen>
  );
}

function Screen({ children, transitionKey }) {
  return <div className="ob-screen" key={transitionKey}>{children}</div>;
}
function ProgressBar({ value }) { return <div className="ob-progress-track"><div className="ob-progress-fill" style={{ width: `${Math.round(value * 100)}%` }} /></div>; }