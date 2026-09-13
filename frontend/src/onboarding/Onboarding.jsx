// frontend/src/onboarding/Onboarding.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, CircleAlert, MapPin, Mic, Pencil, Scissors, Sparkles, Square, Store, Truck, Utensils, Wrench, HardHat, X } from "lucide-react";
import SurveyLayout from "./SurveyLayout.jsx";
import { CATEGORIES, UNIVERSAL_QUESTIONS, CATEGORY_QUESTIONS, WEEKDAYS, EMPLOYEE_OPTIONS } from "./questions.js";

// Por default apunta al backend local de cada quien. Para usar un backend
// compartido (o el desplegado), pongan VITE_API_URL en frontend/.env.local
// — no hace falta tocar este archivo ni recompilar nada mas.
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const STEPS = ["name", "welcome", "otro_detail", "questions", "week_description", "schedule", "employees", "city", "done"];

export default function Onboarding({ ownerId = "demo-owner", onComplete, onExit, active = true }) {
  const [stepIndex, setStepIndex] = useState(1); // Start at "welcome" step (skip "name" in demo)
  const [name, setName] = useState("");
  const [lastName, setLastName] = useState("");
  const [category, setCategory] = useState(null);
  const [otroDetail, setOtroDetail] = useState("");
  const [answers, setAnswers] = useState({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [weekMode, setWeekMode] = useState("text");
  const [weekText, setWeekText] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [recordError, setRecordError] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [days, setDays] = useState([]);
  const [employees, setEmployees] = useState(null);
  const [city, setCity] = useState("");
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const step = STEPS[stepIndex];
  const questions = useMemo(() => {
    if (!category) return [];
    return [...UNIVERSAL_QUESTIONS, ...(CATEGORY_QUESTIONS[category] ?? [])];
  }, [category]);

  // El parametro se llama stepName y no name para no tapar el estado del
  // nombre del usuario, que vive en este mismo scope.
  const goToStep = useCallback((stepName) => setStepIndex(STEPS.indexOf(stepName)), []);

  const pickCategory = (id) => {
    if (id !== category) setAnswers({});
    setCategory(id);
    setQuestionIndex(0);
    goToStep(id === "otro" ? "otro_detail" : "questions");
  };

  const answerQuestion = (value) => {
    const q = questions[questionIndex];
    setAnswers((prev) => ({ ...prev, [q.id]: value }));
    if (questionIndex + 1 < questions.length) setQuestionIndex((i) => i + 1);
    else goToStep("week_description");
  };

  const toggleDay = (id) => setDays((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));

  const detectCity = () => {
    setLocating(true); setLocationError(null);
    if (!navigator.geolocation) {
      setLocating(false);
      setLocationError("Ubicación no disponible, escribe tu ciudad abajo.");
      return;
    }
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
      () => { setLocationError("Ubicación no disponible, escribe tu ciudad abajo."); setLocating(false); },
      { timeout: 10000 }
    );
  };

  const resetRecording = () => {
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordSeconds(0);
    setRecordError(null);
  };

  const startRecording = async () => {
    setRecordError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        streamRef.current?.getTracks().forEach((t) => t.stop());
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setRecording(true);
      setRecordSeconds(0);
      timerRef.current = setInterval(() => setRecordSeconds((s) => s + 1), 1000);
    } catch {
      setRecordError("No pudimos acceder al micrófono. Revisa los permisos o escribe tu respuesta.");
    }
  };

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  }, []);

  const toggleRecording = () => (recording ? stopRecording() : startRecording());

  useEffect(() => {
    if ((weekMode !== "audio" || !active || step !== "week_description") && recording) stopRecording();
  }, [weekMode, active, step, recording, stopRecording]);

  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);

  useEffect(() => () => {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const blobToBase64 = (blob) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const audioBase64 = weekMode === "audio" && audioBlob ? await blobToBase64(audioBlob) : null;
      const res = await fetch(`${API_BASE}/business-profile/${ownerId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category,
          category_detail: category === "otro" ? otroDetail : null,
          operating_days: days,
          city: city.trim(),
          employees,
          answers,
          week_description_mode: weekMode,
          week_description_text: weekMode === "text" ? weekText : null,
          week_description_audio_base64: audioBase64,
          week_description_audio_mime: audioBlob?.type ?? null,
        }),
      });
      // fetch NO lanza error con un 4xx/5xx: hay que revisar res.ok a mano, si no
      // un 500 del backend se veria como guardado exitoso.
      if (!res.ok) throw new Error(`El servidor respondió ${res.status}`);
      setSubmitted(true);
    } catch (err) {
      setSubmitted(false);
      setSubmitError(
        err instanceof TypeError
          ? "No se pudo conectar con el servidor. Revisa tu conexión y vuelve a intentar."
          : err.message,
      );
    } finally {
      setSubmitting(false);
      goToStep("done");
    }
  };

  const categoryLabel = CATEGORIES.find((item) => item.id === category)?.label;
  const categoryIcons = { comida: Utensils, retail: Store, servicios: Wrench, belleza: Scissors, construccion: HardHat, transporte: Truck, otro: Sparkles };
  const dayNames = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  const completedSteps = step === "name" ? 0 : step === "welcome" ? 1 : step === "otro_detail" ? 1.5 : step === "questions" ? 2 + questionIndex : questions.length + 2 + ({ week_description: 0, schedule: 1, employees: 2, city: 3, done: submitted ? 4 : 3 }[step] ?? 0);
  const progress = completedSteps / (questions.length + 6);
  const section = ["name", "welcome", "otro_detail", "questions"].includes(step) ? 0 : ["week_description", "schedule", "employees"].includes(step) ? 1 : 2;

  const goBack = () => {
    if (step === "name") return onExit?.();
    if (step === "welcome") return goToStep("name");
    if (step === "questions") {
      if (questionIndex > 0) setQuestionIndex((index) => index - 1);
      else goToStep(category === "otro" ? "otro_detail" : "welcome");
    } else if (step === "otro_detail") goToStep("welcome");
    else if (step === "week_description") { setQuestionIndex(questions.length - 1); goToStep("questions"); }
    else if (step === "schedule") goToStep("week_description");
    else if (step === "employees") goToStep("schedule");
    else if (step === "city") goToStep("employees");
    else goToStep("city");
  };

  const controls = (onNext, label = "Continuar", disabled = false) => (
    <div className="survey-controls">
      <button type="button" className="entry-back" onClick={goBack} disabled={submitting}
        aria-label={step === "questions" ? "Volver a la pregunta anterior" : "Volver al paso anterior"}>
        <ArrowLeft size={16} aria-hidden /> Atrás
      </button>
      {onNext && <button type="button" className="entry-primary" onClick={onNext} disabled={disabled || submitting}>{label}<ArrowRight size={16} aria-hidden /></button>}
    </div>
  );

  // El nombre se queda en el cliente: solo alimenta el saludo de la app y el
  // reverso de la tarjeta. No viaja en el POST porque el esquema del backend
  // (y las columnas de Snowflake) no tienen dónde guardarlo todavía.
  // Los espacios de sobra se colapsan: "Ana  María" es un nombre, no dos.
  const trimmedName = name.trim().replace(/\s+/g, " ");
  const trimmedLastName = lastName.trim().replace(/\s+/g, " ");
  const identity = { name: trimmedName, lastName: trimmedLastName };

  let title, description, kicker, content;
  if (step === "name") {
    title = "¿Cómo te llamas?";
    description = "Así sabemos cómo saludarte dentro de la app y qué nombre va en tu tarjeta.";
    kicker = "01 / Mucho gusto";
    content = <>
      <label className="survey-field">Tu nombre (o nombres)<input placeholder="Ej. Carlos Alberto" autoComplete="given-name" value={name} onChange={(event) => setName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && trimmedName) goToStep("welcome"); }} /></label>
      <label className="survey-field">Tus apellidos<input placeholder="Ej. Tabares Quiroz" autoComplete="family-name" value={lastName} onChange={(event) => setLastName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && trimmedName) goToStep("welcome"); }} /></label>
      {controls(() => goToStep("welcome"), "Continuar", !trimmedName)}
    </>;
  } else if (step === "welcome") {
    title = "Selecciona tu modelo de negocio";
    description = "Elige la opción que mejor describe lo que haces. A partir de aquí, la encuesta se adapta a ti.";
    kicker = "01 / Empecemos por lo tuyo";
    content = <>
      <div className="survey-categories">
        {CATEGORIES.map((item) => {
          const Icon = categoryIcons[item.id];
          return <button key={item.id} className="survey-category" aria-pressed={category === item.id} onClick={() => pickCategory(item.id)}><Icon size={23} aria-hidden /><span>{item.label}</span></button>;
        })}
      </div>
      <div className="survey-controls"><button className="entry-back" onClick={onExit}><ArrowLeft size={16} aria-hidden /> Inicio</button><button className="ob-link-btn" onClick={() => onComplete?.({ category: null, answers: {}, ...identity })}>Saltar encuesta</button></div>
    </>;
  } else if (step === "otro_detail") {
    title = "Cuéntanos, ¿a qué se dedica tu negocio?";
    description = "Cada negocio es distinto. Describe el tuyo en unas palabras.";
    kicker = "01 / Tu negocio, a tu manera";
    content = <>
      <label className="survey-field">Actividad de tu negocio<input placeholder="Ej. Taller de bicicletas" value={otroDetail} onChange={(event) => setOtroDetail(event.target.value)} /></label>
      {controls(() => goToStep("questions"), "Continuar", !otroDetail.trim())}
    </>;
  } else if (step === "questions") {
    const question = questions[questionIndex];
    title = question.text;
    description = "Piensa en cómo trabajas normalmente. Puedes volver y cambiar tu respuesta.";
    kicker = `${categoryLabel} / Pregunta ${questionIndex + 1} de ${questions.length}`;
    content = <>
      <div className="survey-choice-list">
        <button className="survey-choice" aria-pressed={answers[question.id] === false} onClick={() => answerQuestion(false)}><X size={22} aria-hidden /> No</button>
        <button className="survey-choice" aria-pressed={answers[question.id] === true} onClick={() => answerQuestion(true)}><Check size={22} aria-hidden /> Sí</button>
      </div>
      <p className="survey-auto-note">Al elegir, pasas a la siguiente pregunta.</p>
      {controls()}
    </>;
  } else if (step === "week_description") {
    title = "Cuéntanos cómo es una semana normal en tu negocio";
    description = "¿Cuándo compras, cuándo vendes más y cómo te organizas? Puedes escribirlo o contárnoslo con tu voz.";
    kicker = "02 / Tu día a día";
    content = <>
      <div className="survey-mode" role="group" aria-label="Cómo quieres responder">
        <button aria-pressed={weekMode === "text"} onClick={() => setWeekMode("text")}><Pencil size={16} aria-hidden /> Escribir</button>
        <button aria-pressed={weekMode === "audio"} onClick={() => setWeekMode("audio")}><Mic size={16} aria-hidden /> Narrar</button>
      </div>
      {weekMode === "text" ? <label className="survey-field">Tu semana en pocas palabras
        <textarea placeholder="Ej. Los lunes recibo mercancía, entre semana atiendo el local y los fines de semana vendo más…" value={weekText} onChange={(event) => setWeekText(event.target.value)} rows={5} />
      </label> : <div className="ob-recorder">
        <button type="button" className={`ob-mic-btn ${recording ? "ob-mic-btn--recording" : ""}`} onClick={toggleRecording} aria-label={recording ? "Detener grabación" : "Iniciar grabación"}>
          {recording && <span className="ob-mic-btn__ring" aria-hidden />}
          {recording ? <Square size={24} aria-hidden /> : <Mic size={28} aria-hidden />}
        </button>
        <p className="ob-recorder-status" role="status">{recording ? `Grabando… ${formatTime(recordSeconds)}` : audioUrl ? "Grabación lista" : "Toca para grabar"}</p>
        {recordError && <p className="ob-error" role="alert">{recordError}</p>}
        {audioUrl && !recording && <div className="ob-recorder-playback"><audio controls src={audioUrl} /><button className="ob-link-btn" onClick={resetRecording}>Grabar de nuevo</button></div>}
      </div>}
      {controls(() => goToStep("schedule"), "Continuar", weekMode === "text" ? !weekText.trim() : !audioBlob || recording)}
    </>;
  } else if (step === "schedule") {
    title = "¿Qué días opera tu negocio?";
    description = "Selecciona todos los días que trabajas en tu negocio.";
    kicker = "02 / A tu ritmo";
    content = <>
      <div className="survey-days bubble-grid" role="group" aria-label="Días de operación">
        {WEEKDAYS.map((day, index) => <button key={day.id} aria-label={dayNames[index]} aria-pressed={days.includes(day.id)} onClick={() => toggleDay(day.id)}>{dayNames[index].slice(0, 3)}</button>)}
      </div>
      <p className="survey-auto-note" role="status">{days.length ? `${days.length} ${days.length === 1 ? "día seleccionado" : "días seleccionados"}` : "Puedes elegir más de uno."}</p>
      {controls(() => goToStep("employees"), "Continuar", days.length === 0)}
    </>;
  } else if (step === "employees") {
    title = "¿Cuántas personas trabajan contigo?";
    description = "Conocer el tamaño de tu equipo nos ayuda a entender tu operación.";
    kicker = "02 / Las personas detrás de tu negocio";
    content = <>
      <div className="survey-choice-list survey-choice-list--employees">{EMPLOYEE_OPTIONS.map((item) => <button key={item.id} className="survey-choice survey-choice--employee" aria-pressed={employees === item.id} onClick={() => { setEmployees(item.id); goToStep("city"); }}>{item.label}</button>)}</div>
      <p className="survey-auto-note">Al elegir, pasas al último paso.</p>
      {controls()}
    </>;
  } else if (step === "city") {
    title = "¿En qué ciudad opera tu negocio?";
    description = "Un último detalle para completar tu perfil.";
    kicker = "03 / Ya casi está";
    content = <>
      <button className="entry-secondary" onClick={detectCity} disabled={locating || submitting}><MapPin size={17} aria-hidden />{locating ? "Buscando…" : "Usar mi ubicación"}</button>
      {locationError && <p className="ob-error" role="alert">{locationError}</p>}
      <label className="survey-field">Ciudad<input placeholder="O escribe tu ciudad" autoComplete="address-level2" value={city} disabled={submitting} onChange={(event) => setCity(event.target.value)} /></label>
      {controls(submit, submitting ? "Guardando…" : "Terminar", !city.trim())}
    </>;
  } else {
    title = submitted ? "¡Listo! Tu siguiente paso empieza aquí." : "No se pudo guardar";
    description = submitted ? "Tu perfil de negocio quedó guardado." : "Tus respuestas siguen aquí — puedes reintentar sin volver a capturarlas.";
    kicker = submitted ? "03 / Un espacio que ya es tuyo" : "Tu perfil sigue contigo";
    content = <>
      <div className={`survey-success-icon ${submitted ? "" : "survey-success-icon--error"}`}>{submitted ? <Check size={28} aria-hidden /> : <CircleAlert size={28} aria-hidden />}</div>
      {!submitted && submitError && <p className="ob-error" role="alert">{submitError}</p>}
      {submitted && <dl className="survey-summary"><div><dt>Tu negocio</dt><dd>{categoryLabel}</dd></div><div><dt>Ciudad</dt><dd>{city.trim()}</dd></div><div><dt>Días de operación</dt><dd>{days.length} a la semana</dd></div></dl>}
      {submitted
        ? <button className="entry-primary" onClick={() => onComplete?.({ category, answers, ...identity })}>Ir a mi cuenta<ArrowRight size={16} aria-hidden /></button>
        : controls(submit, submitting ? "Guardando…" : "Reintentar")}
    </>;
  }

  return <SurveyLayout section={section} progress={progress} stepKey={`${step}-${questionIndex}`} title={title} description={description} kicker={kicker} onExit={onExit} busy={submitting} active={active}>{content}</SurveyLayout>;
}
