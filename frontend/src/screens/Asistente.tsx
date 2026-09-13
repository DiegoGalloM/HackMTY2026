import { useEffect, useRef, useState } from "react";
import { BookOpen, Database, SendHorizontal, Sparkles } from "lucide-react";
import type { AssistantAnswer } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import Screen from "../components/Screen";
import { NoSessionState } from "../components/ui";

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  answer?: AssistantAnswer;
  error?: boolean;
}

const STARTERS = ["¿Cómo van mis ventas esta semana?", "¿Cómo está mi liquidez?", "¿Por qué bajó mi utilidad este mes?", "¿Qué insumo se me va a acabar primero?", "¿Qué es el capital de trabajo?"];

/** "Pregúntale lo que sea a tu negocio": respuestas con evidencia de tus datos. */
export default function Asistente() {
  const { api, businessName } = useBusiness();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  if (!api) {
    return (
      <Screen title="Asistente">
        <NoSessionState />
      </Screen>
    );
  }

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { id: Date.now(), role: "user", text: q }]);
    setBusy(true);
    const res = await api.ask(q);
    setBusy(false);
    if (res.ok) {
      setMessages((m) => [...m, { id: Date.now() + 1, role: "assistant", text: res.data.answer, answer: res.data }]);
      if (res.data.suggestions?.length) setSuggestions(res.data.suggestions);
    } else {
      setMessages((m) => [...m, { id: Date.now() + 1, role: "assistant", text: res.message, error: true }]);
    }
  };

  return (
    <Screen>
      <header className="px-5 pt-8">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">Asistente</p>
        <h1 className="text-2xl font-semibold tracking-tight">Pregúntale a {businessName}</h1>
        <p className="mt-1 text-xs text-muted">Responde con tus ventas, inventario y libros reales. Te muestra de dónde salió cada número.</p>
      </header>

      <div className="mt-4 space-y-3 px-5" aria-live="polite">
        {messages.length === 0 && (
          <div className="rounded-2xl bg-white px-4 py-4 text-sm ring-1 ring-black/5">
            <p className="flex items-center gap-2 font-semibold">
              <Sparkles size={16} className="text-brand" aria-hidden /> Hola. ¿Qué quieres saber de tu negocio?
            </p>
            <p className="mt-1 text-xs text-muted">Puedes preguntar por ventas, ganancia, inventario, caja, gastos, clientes o qué significa un término.</p>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "bg-brand text-white" : m.error ? "bg-accent/10 text-ink" : "bg-white text-ink ring-1 ring-black/5"}`} role={m.error ? "alert" : undefined}>
              <p className="whitespace-pre-wrap">{m.text}</p>
              {m.answer && m.answer.evidence.length > 0 && (
                <ul className="mt-3 grid grid-cols-2 gap-2" aria-label="Evidencia">
                  {m.answer.evidence.map((e, i) => (
                    <li key={i} className="rounded-xl bg-tile px-2.5 py-2">
                      <p className="text-[10px] font-semibold tracking-wide text-muted uppercase">{e.label}</p>
                      <p className="text-sm font-semibold tabular-nums">{e.value}</p>
                      {e.detail && <p className="text-[10px] text-muted">{e.detail}</p>}
                    </li>
                  ))}
                </ul>
              )}
              {m.answer && (
                <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-muted">
                  {m.answer.sources.some((s) => s.type === "structured") && (
                    <span className="inline-flex items-center gap-1">
                      <Database size={10} aria-hidden /> Datos de tu negocio
                    </span>
                  )}
                  {m.answer.sources
                    .filter((s) => s.type === "knowledge")
                    .map((s) => (
                      <span key={s.id ?? s.title} className="inline-flex items-center gap-1">
                        <BookOpen size={10} aria-hidden /> {s.title}
                      </span>
                    ))}
                  {m.answer.llm_used && <span>· redactado por IA ({m.answer.llm_provider})</span>}
                </p>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-white px-4 py-3 text-sm text-muted ring-1 ring-black/5" role="status">
              Consultando tus datos…
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="mt-4 px-5">
        <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Sugerencias">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => ask(s)} disabled={busy} className="shrink-0 rounded-full bg-white px-3 py-1.5 text-xs font-medium ring-1 ring-black/10 disabled:opacity-50">
              {s}
            </button>
          ))}
        </div>
        <form
          className="mt-3 flex items-center gap-2 rounded-full bg-white p-1.5 ring-1 ring-black/10"
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
        >
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Escribe tu pregunta…" aria-label="Pregunta" className="min-w-0 flex-1 bg-transparent px-3 text-sm outline-none" />
          <button type="submit" disabled={busy || !input.trim()} aria-label="Enviar" className="flex size-9 items-center justify-center rounded-full bg-brand text-white disabled:opacity-40">
            <SendHorizontal size={16} aria-hidden />
          </button>
        </form>
      </div>
    </Screen>
  );
}
