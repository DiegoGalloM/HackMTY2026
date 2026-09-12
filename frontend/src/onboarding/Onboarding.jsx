// frontend/src/onboarding/Onboarding.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bubble, BubbleGrid } from "./Bubble.jsx";
import { CATEGORIES, UNIVERSAL_QUESTIONS, CATEGORY_QUESTIONS, WEEKDAYS, EMPLOYEE_OPTIONS } from "./questions.js";

const API_BASE = "http://localhost:8000";
const STEPS = ["welcome", "otro_detail", "questions", "week_description", "schedule", "employees", "city", "done"];

export default function Onboarding({ ownerId = "demo-owner", onComplete }) {
  const [stepIndex, setStepIndex] = useState(0);
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

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const step = STEPS[stepIndex];
  const questions = useMemo(() => {
    if (!category) return [];
    return [...UNIVERSAL_QUESTIONS, ...(CATEGORY_QUESTIONS[category] ?? [])];
  }, [category]);

  const goToStep = useCallback((name) => setStepIndex(STEPS.indexOf(name)), []);

  const pickCategory = (id) => {
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

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    clearInterval(timerRef.current);
  };

  const toggleRecording = () => (recording ? stopRecording() : startRecording());

  useEffect(() => {
    if (weekMode !== "audio" && recording) stopRecording();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weekMode]);

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
    setSubmitting(true);
    try {
      const audioBase64 = weekMode === "audio" && audioBlob ? await blobToBase64(audioBlob) : null;
      await fetch(`${API_BASE}/business-profile/${ownerId}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category,
          category_detail: category === "otro" ? otroDetail : null,
          operating_days: days,
          city,
          employees,
          answers,
          week_description_mode: weekMode,
          week_description_text: weekMode === "text" ? weekText : null,
          week_description_audio_base64: audioBase64,
          week_description_audio_mime: audioBlob?.type ?? null,
        }),
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
      {/* Atajo para demos/dev: brinca toda la encuesta sin guardar perfil. */}
      <button type="button" className="ob-link-btn" onClick={() => onComplete?.()}>
        Saltar encuesta
      </button>
    </Screen>
  );

  if (step === "otro_detail") return (
    <Screen transitionKey="otro_detail">
      <p className="ob-subtitle">Cuéntanos, ¿a qué se dedica tu negocio?</p>
      <input
        className="ob-input"
        placeholder="Ej. Taller de bicicletas"
        value={otroDetail}
        onChange={(e) => setOtroDetail(e.target.value)}
        autoFocus
      />
      <button className="ob-continue" disabled={!otroDetail.trim()} onClick={() => goToStep("questions")}>Continuar</button>
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

  if (step === "week_description") return (
    <Screen transitionKey="week_description">
      <p className="ob-subtitle">Cuéntanos cómo es una semana normal en tu negocio</p>

      <div className="ob-mode-toggle" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={weekMode === "text"}
          className={`ob-mode-btn ${weekMode === "text" ? "ob-mode-btn--active" : ""}`}
          onClick={() => setWeekMode("text")}
        >
          <PencilIcon /> Escribir
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={weekMode === "audio"}
          className={`ob-mode-btn ${weekMode === "audio" ? "ob-mode-btn--active" : ""}`}
          onClick={() => setWeekMode("audio")}
        >
          <MicIcon size={16} /> Narrar
        </button>
      </div>

      {weekMode === "text" ? (
        <textarea
          className="ob-textarea"
          placeholder="Ej. Los lunes recibo mercancía, entre semana atiendo el local de 9 a 6, los fines de semana es cuando más vendo…"
          value={weekText}
          onChange={(e) => setWeekText(e.target.value)}
          rows={5}
        />
      ) : (
        <div className="ob-recorder">
          <button
            type="button"
            className={`ob-mic-btn ${recording ? "ob-mic-btn--recording" : ""}`}
            onClick={toggleRecording}
            aria-label={recording ? "Detener grabación" : "Iniciar grabación"}
          >
            {recording && <span className="ob-mic-btn__ring" aria-hidden="true" />}
            {recording ? <StopIcon /> : <MicIcon size={28} />}
          </button>

          {recording && (
            <div className="ob-wave" aria-hidden="true">
              <span /><span /><span /><span /><span />
            </div>
          )}

          <p className="ob-recorder-status">
            {recording ? `Grabando… ${formatTime(recordSeconds)}` : audioUrl ? "Grabación lista" : "Toca para grabar"}
          </p>
          {recordError && <p className="ob-error">{recordError}</p>}

          {audioUrl && !recording && (
            <div className="ob-recorder-playback">
              <audio controls src={audioUrl} />
              <button type="button" className="ob-link-btn" onClick={resetRecording}>Grabar de nuevo</button>
            </div>
          )}
        </div>
      )}

      <button
        className="ob-continue"
        disabled={weekMode === "text" ? !weekText.trim() : !audioBlob}
        onClick={() => goToStep("schedule")}
      >
        Continuar
      </button>
    </Screen>
  );

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
      <button className="ob-continue" onClick={() => onComplete?.()}>Ir a mi cuenta</button>
    </Screen>
  );
}

function Screen({ children, transitionKey }) {
  return <div className="ob-screen" key={transitionKey}>{children}</div>;
}
function ProgressBar({ value }) { return <div className="ob-progress-track"><div className="ob-progress-fill" style={{ width: `${Math.round(value * 100)}%` }} /></div>; }

function MicIcon({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}
