// Piezas de UI compartidas por las pantallas financieras. Mismo lenguaje
// visual que Cuenta: tarjetas blancas redondeadas sobre bg-surface, tiles
// grises, azul de marca para acciones.
import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, LoaderCircle, RefreshCw } from "lucide-react";
import type { ApiError } from "../api/client";
import type { Status } from "../api/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl bg-white px-4 py-4 shadow-sm ring-1 ring-black/5 ${className}`}>{children}</div>;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-muted">{children}</h2>
      {action}
    </div>
  );
}

const STATUS_STYLES: Record<Status, string> = {
  good: "bg-positive/10 text-positive",
  attention: "bg-amber-100 text-amber-800",
  critical: "bg-accent/10 text-accent",
  neutral: "bg-tile text-muted",
  info: "bg-brand/10 text-brand",
};

export const STATUS_LABELS: Record<Status, string> = {
  good: "Bien",
  attention: "Atención",
  critical: "Urgente",
  neutral: "Sin datos",
  info: "Info",
};

export function StatusPill({ status, label }: { status: Status; label?: string }) {
  return <span className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${STATUS_STYLES[status]}`}>{label ?? STATUS_LABELS[status]}</span>;
}

export function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "positive" | "negative" | "neutral" }) {
  const color = tone === "positive" ? "text-positive" : tone === "negative" ? "text-accent" : "text-ink";
  return (
    <div className="min-w-0">
      <p className="text-xs text-muted">{label}</p>
      <p className={`truncate text-lg font-semibold tabular-nums ${color}`}>{value}</p>
      {hint && <p className="text-[11px] text-muted">{hint}</p>}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  className = "",
  busy,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
  busy?: boolean;
}) {
  const styles = {
    primary: "bg-brand text-white",
    secondary: "bg-tile text-ink",
    ghost: "bg-transparent text-brand",
    danger: "bg-accent text-white",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || busy}
      aria-busy={busy}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-4 text-sm font-semibold transition-transform active:scale-[0.98] disabled:opacity-40 ${styles} ${className}`}
    >
      {busy && <LoaderCircle size={16} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-semibold text-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-muted">{hint}</span>}
    </label>
  );
}

export const inputClass = "w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm text-ink outline-none focus:border-brand";

export function LoadingState({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 px-5 py-10 text-sm text-muted" role="status">
      <LoaderCircle size={18} className="animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="mx-5 my-4 rounded-2xl bg-accent/5 px-4 py-4 text-sm" role="alert">
      <div className="flex items-start gap-2">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <p className="text-ink">{error.message}</p>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand">
          <RefreshCw size={14} aria-hidden /> Reintentar
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="mx-5 my-4 rounded-2xl bg-tile px-4 py-6 text-center">
      <p className="text-sm font-semibold">{title}</p>
      {body && <p className="mt-1 text-xs text-muted">{body}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function NoSessionState() {
  return (
    <EmptyState
      title="Inicia sesión para ver tu negocio"
      body="Tus ventas, inventario y libros viven en tu cuenta. Vuelve al inicio y entra o explora la demo."
    />
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "success"; children: ReactNode }) {
  const Icon = tone === "success" ? CheckCircle2 : Info;
  const styles = tone === "success" ? "bg-positive/10 text-positive" : "bg-brand/10 text-brand";
  return (
    <div className={`flex items-start gap-2 rounded-xl px-3 py-2 text-xs ${styles}`} role="status">
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden />
      <span className="text-ink">{children}</span>
    </div>
  );
}

/**
 * Pestañas en píldora. Con `scroll`, las opciones no se comprimen: la fila se
 * desliza horizontalmente (para cinco pestañas en los 362 px del celular).
 */
export function Segmented<T extends string>({ value, options, onChange, scroll = false }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; scroll?: boolean }) {
  return (
    <div className={`flex rounded-full bg-tile p-1 ${scroll ? "no-scrollbar max-w-full overflow-x-auto" : ""}`} role="tablist">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="tab"
          aria-selected={value === opt.value}
          onClick={() => onChange(opt.value)}
          className={`${scroll ? "shrink-0 whitespace-nowrap" : "flex-1"} rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${value === opt.value ? "bg-white text-brand shadow-sm" : "text-muted"}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
