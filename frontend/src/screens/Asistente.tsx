import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart3, BookOpen, Database, SendHorizontal, Sparkles } from "lucide-react";
import { formatMoney } from "../api/format";
import type { AssistantAnswer, AttentionItem, Health } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import { NoSessionState, StatusPill } from "../components/ui";

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  answer?: AssistantAnswer;
  error?: boolean;
}

const STARTERS = ["¿Cómo van mis ventas esta semana?", "¿Cómo está mi liquidez?", "¿Por qué bajó mi utilidad este mes?", "¿Qué insumo se me va a acabar primero?", "¿Qué es el capital de trabajo?"];
const CONCEPT_STARTERS = ["¿Qué es el capital de trabajo?", "¿Qué es el margen bruto?", "¿Qué es la liquidez?", "¿Cómo se calcula la razón circulante?"];

/** Cada punto de atención se vuelve una pregunta que el asistente sabe enrutar. */
const ATTENTION_QUESTIONS: Record<string, string> = {
  cash: "¿Cómo está mi caja?",
  margin: "¿Cómo va mi margen este mes?",
  stock: "¿Qué insumo se me va a acabar primero?",
  overstock: "¿Cuánto inventario tengo?",
  review: "¿Cuánto gasté con la tarjeta este mes?",
  profit_drop: "¿Por qué bajó mi utilidad este mes?",
};

const questionFor = (a: AttentionItem) => ATTENTION_QUESTIONS[a.id] ?? `¿Qué pasa con esto: ${a.title.toLowerCase()}?`;

/**
 * "Pregúntale lo que sea a tu negocio". Es la pantalla del botón central
 * (Análisis): primero la conversación, con un resumen de apertura calculado
 * por el backend; los datos completos quedan un toque más allá (Ver resumen).
 *
 * Cada pregunta es independiente: el asistente no guarda conversación y la
 * transcripción vive sólo mientras la pantalla esté montada.
 */
export default function Asistente() {
  const { api, businessName } = useBusiness();
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  // El resumen de apertura sólo hace falta con la conversación vacía; con
  // mensajes no se pide (y si falla, la charla sigue con la bienvenida fija).
  const empty = messages.length === 0;
  const health = useBusinessQuery<Health | null>((a) => (empty ? a.health("week") : Promise.resolve({ ok: true, data: null })), [empty]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  if (!api) {
    return (
      <Screen title="Análisis">
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

  const brief = empty && health.data ? buildBrief(health.data) : null;
  const chips = brief ? brief.chips : suggestions;

  return (
    <Screen>
      <header className="px-5 pt-8">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-wide text-muted uppercase">Análisis</p>
            <h1 className="text-2xl font-semibold tracking-tight">Pregúntale a {businessName}</h1>
          </div>
          <Link to="/resumen" className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full bg-tile px-3 text-xs font-semibold text-ink">
            <BarChart3 size={14} aria-hidden /> Ver resumen
          </Link>
        </div>
        <p className="mt-1 text-xs text-muted">Responde con tus ventas, inventario y libros reales. Te muestra de dónde salió cada número.</p>
      </header>

      <div className="mt-4 space-y-3 px-5" aria-live="polite">
        {empty && (brief ? <BriefCard brief={brief} /> : <WelcomeCard loading={health.loading} />)}
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
        <div className="no-scrollbar flex gap-2 overflow-x-auto pb-1" aria-label="Sugerencias">
          {chips.map((s) => (
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

// ------------------------------------------------------ resumen de apertura --

interface Brief {
  noSales: boolean;
  headline: string;
  status: Health["cash"]["status"];
  sales: string;
  attention: AttentionItem[];
  chips: string[];
}

/** Primer mensaje del asistente, calculado en el cliente a partir del panel
 * de salud (cero llamadas al LLM): el estado de la caja, las ventas de la
 * semana y cada punto de atención en una línea, con su pregunta lista. */
function buildBrief(h: Health): Brief {
  const noSales = h.revenue.value === 0 && h.orders.value === 0;
  const attentionChips = h.attention.map(questionFor);
  const chips = noSales ? CONCEPT_STARTERS : [...new Set([...attentionChips, ...STARTERS])].slice(0, 7);
  return {
    noSales,
    headline: h.cash.headline,
    status: h.cash.status,
    sales: `${formatMoney(h.revenue.value)} en ${h.orders.value} ${h.orders.value === 1 ? "venta" : "ventas"} ${h.period.label}`,
    attention: h.attention,
    chips,
  };
}

function BriefCard({ brief }: { brief: Brief }) {
  return (
    <div className="rounded-2xl bg-white px-4 py-4 text-sm ring-1 ring-black/5" data-testid="opening-brief">
      <p className="flex items-center gap-2 font-semibold">
        <Sparkles size={16} className="text-brand" aria-hidden /> Así va tu negocio hoy
      </p>
      {brief.noSales ? (
        <p className="mt-2 text-xs text-muted">
          Todavía no hay ventas registradas. En cuanto cobres con QR desde{" "}
          <Link to="/vender" className="font-semibold text-brand">
            Vender
          </Link>
          , aquí verás cómo va el negocio. Mientras, pregúntame qué significa cualquier término.
        </p>
      ) : (
        <>
          <div className="mt-3 flex items-center justify-between gap-2">
            <p className="font-medium">{brief.headline}</p>
            <StatusPill status={brief.status} />
          </div>
          <p className="mt-1 text-xs text-muted">Ventas: {brief.sales}.</p>
          {brief.attention.length > 0 && (
            <ul className="mt-3 space-y-1.5 border-t border-black/5 pt-3">
              {brief.attention.map((a) => (
                <li key={a.id} className="flex items-start gap-2 text-xs">
                  <StatusPill status={a.severity} />
                  <span>
                    <span className="font-semibold">{a.title}.</span> <span className="text-muted">{a.body}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs text-muted">Toca un tema abajo o escribe tu pregunta.</p>
        </>
      )}
    </div>
  );
}

function WelcomeCard({ loading }: { loading: boolean }) {
  return (
    <div className="rounded-2xl bg-white px-4 py-4 text-sm ring-1 ring-black/5">
      <p className="flex items-center gap-2 font-semibold">
        <Sparkles size={16} className="text-brand" aria-hidden /> Hola. ¿Qué quieres saber de tu negocio?
      </p>
      <p className="mt-1 text-xs text-muted">{loading ? "Revisando tus números de la semana…" : "Puedes preguntar por ventas, ganancia, inventario, caja, gastos, clientes o qué significa un término."}</p>
    </div>
  );
}
