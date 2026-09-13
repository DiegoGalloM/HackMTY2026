import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, ChevronDown, LoaderCircle, ShieldCheck } from "lucide-react";
import { getCheckout, payCheckout } from "../api/finance";
import { formatMoney } from "../api/format";
import type { CheckoutView } from "../api/types";
import CapitalOneLogo from "../components/CapitalOneLogo";

/**
 * Página pública de pago: lo que abre el cliente al escanear el QR.
 * Sin cuenta, sin capturar qué compra ni cuánto: eso lo definió el vendedor.
 * La app nunca pide ni guarda el número completo de la tarjeta.
 */
export default function Pay() {
  const { token = "" } = useParams();
  const [view, setView] = useState<CheckoutView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [customer, setCustomer] = useState({ name: "", email: "" });

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getCheckout(token).then((res) => {
      if (!alive) return;
      setLoading(false);
      if (res.ok) setView(res.data);
      else setError(res.kind === "not_found" ? "Este código de pago no existe o ya venció." : res.message);
    });
    return () => {
      alive = false;
    };
  }, [token]);

  const pay = async () => {
    setPaying(true);
    setError(null);
    const res = await payCheckout(token, {
      card_last4: "4242",
      customer_name: customer.name.trim() || undefined,
      customer_email: customer.email.trim() || undefined,
    });
    setPaying(false);
    if (res.ok) setView(res.data);
    else setError(res.message);
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-surface">
      <header className="flex items-center justify-between px-5 pt-12 pb-4">
        <CapitalOneLogo business className="text-[18px] text-navy" />
        <span className="rounded-full bg-tile px-2 py-0.5 text-[10px] font-semibold text-muted">{view?.provider.mode === "test" ? "Pago de prueba" : "Pago seguro"}</span>
      </header>

      {loading && (
        <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted" role="status">
          <LoaderCircle size={18} className="animate-spin" aria-hidden /> Cargando tu orden…
        </div>
      )}

      {!loading && !view && (
        <div className="px-5" role="alert">
          <h1 className="text-xl font-semibold">No encontramos esta orden</h1>
          <p className="mt-2 text-sm text-muted">{error}</p>
        </div>
      )}

      {view && view.status === "PAID" && (
        <div className="px-5 text-center">
          <CheckCircle2 size={56} className="mx-auto mt-6 text-positive" aria-hidden />
          <h1 className="mt-3 text-2xl font-semibold">¡Pago realizado!</h1>
          <p className="mt-1 text-sm text-muted">{view.business_name}</p>
          <p className="mt-4 text-4xl font-semibold tabular-nums">{formatMoney(view.total)}</p>
          {view.payment?.card_last4 && <p className="mt-1 text-xs text-muted">Tarjeta terminada en {view.payment.card_last4}</p>}
          <ul className="mx-auto mt-6 max-w-xs divide-y divide-black/5 rounded-2xl bg-white text-left text-sm ring-1 ring-black/5">
            {view.lines.map((l, i) => (
              <li key={i} className="flex justify-between px-4 py-2">
                <span>
                  {l.quantity} × {l.item_name}
                </span>
                <span className="tabular-nums">{formatMoney(l.line_total)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-xs text-muted">Orden #{view.order_number}. Ya puedes cerrar esta página.</p>
        </div>
      )}

      {view && view.status === "CANCELLED" && (
        <div className="px-5" role="alert">
          <h1 className="text-xl font-semibold">Esta orden fue cancelada</h1>
          <p className="mt-2 text-sm text-muted">Pídele al negocio que genere un nuevo código.</p>
        </div>
      )}

      {view && view.status === "AWAITING_PAYMENT" && (
        <div className="flex flex-1 flex-col px-5">
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">Estás pagando a</p>
          <h1 className="text-2xl font-semibold">{view.business_name}</h1>

          <ul className="mt-5 divide-y divide-black/5 rounded-2xl bg-white ring-1 ring-black/5" aria-label="Detalle de la compra">
            {view.lines.map((l, i) => (
              <li key={i} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>
                  <span className="font-semibold">{l.quantity} ×</span> {l.item_name}
                </span>
                <span className="tabular-nums">{formatMoney(l.line_total)}</span>
              </li>
            ))}
            {view.tax_total > 0 && (
              <li className="flex items-center justify-between px-4 py-2 text-xs text-muted">
                <span>Incluye impuesto sobre ventas</span>
                <span className="tabular-nums">{formatMoney(view.tax_total)}</span>
              </li>
            )}
          </ul>

          <div className="mt-6 text-center">
            <p className="text-xs text-muted">Total</p>
            <p className="text-4xl font-semibold tabular-nums">{formatMoney(view.total)}</p>
          </div>

          <button type="button" onClick={() => setShowDetails((s) => !s)} className="mt-5 inline-flex items-center gap-1 self-center text-xs font-semibold text-brand" aria-expanded={showDetails}>
            ¿Quieres tu recibo por correo? <ChevronDown size={14} className={showDetails ? "rotate-180" : ""} aria-hidden />
          </button>
          {showDetails && (
            <div className="mt-2 space-y-2">
              <input className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm" placeholder="Tu nombre (opcional)" value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} autoComplete="name" />
              <input className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm" placeholder="Tu correo (opcional)" type="email" value={customer.email} onChange={(e) => setCustomer({ ...customer, email: e.target.value })} autoComplete="email" />
            </div>
          )}

          {error && (
            <p className="mt-3 text-center text-xs text-accent" role="alert">
              {error}
            </p>
          )}

          <div className="mt-auto pb-8 pt-6">
            <button type="button" onClick={pay} disabled={paying} aria-busy={paying} className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full bg-brand text-base font-semibold text-white shadow-[0_8px_20px_rgba(0,73,119,.28)] transition-transform active:scale-[.98] disabled:opacity-50">
              {paying ? <LoaderCircle size={18} className="animate-spin" aria-hidden /> : <ShieldCheck size={18} aria-hidden />}
              {paying ? "Procesando…" : `Pagar ${formatMoney(view.total)}`}
            </button>
            <p className="mt-3 text-center text-[11px] text-muted">
              {view.provider.mode === "test" ? "Modo de prueba: no se cobra ninguna tarjeta real." : "Pago procesado de forma segura. No guardamos tu tarjeta."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
