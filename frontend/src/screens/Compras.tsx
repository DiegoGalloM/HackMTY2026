import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { CreditCard, Receipt, RefreshCw, Sparkles, X } from "lucide-react";
import type { BusinessApi } from "../api/finance";
import { formatDateTime, formatMoney, formatQty } from "../api/format";
import type { CardTransaction, ClassificationKind, SampleReceiptItem } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import BottomSheet from "../components/BottomSheet";
import Screen from "../components/Screen";
import { Button, Card, EmptyState, ErrorState, LoadingState, NoSessionState, Notice, SectionTitle, Stat, StatusPill } from "../components/ui";

// Preguntas en lenguaje de negocio, nunca "elige la cuenta de cargo".
const KIND_OPTIONS: { kind: ClassificationKind; label: string; emoji: string }[] = [
  { kind: "INVENTORY", label: "Inventario / mercancía", emoji: "📦" },
  { kind: "EQUIPMENT", label: "Equipo o herramienta", emoji: "🛠️" },
  { kind: "EXPENSE", label: "Gasto del negocio", emoji: "🧾" },
  { kind: "PERSONAL", label: "Compra personal", emoji: "🙋" },
];

/**
 * Compras: lo que la tarjeta de negocio registró automáticamente. El dueño
 * solo confirma las dudosas y, si quiere, agrega el ticket para que el
 * inventario se actualice con cantidades.
 */
export default function Compras() {
  const { api, refresh } = useBusiness();
  const purchases = useBusinessQuery((a) => a.purchases());
  const spending = useBusinessQuery((a) => a.spending("month"));
  const [simulating, setSimulating] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const [receiptFor, setReceiptFor] = useState<CardTransaction | null>(null);
  const [classifying, setClassifying] = useState<string | null>(null);

  if (!api) {
    return (
      <Screen title="Compras">
        <NoSessionState />
      </Screen>
    );
  }

  const list = purchases.data ?? [];
  const pending = list.filter((t) => t.needs_review);
  const rest = list.filter((t) => !t.needs_review);

  const simulate = async () => {
    setSimulating(true);
    setSimError(null);
    const res = await api.simulatePurchase();
    setSimulating(false);
    if (!res.ok) {
      setSimError(res.message);
      return;
    }
    refresh();
  };

  const classify = async (tx: CardTransaction, kind: ClassificationKind) => {
    setClassifying(tx.transaction_id);
    const res = await api.classify(tx.transaction_id, kind);
    setClassifying(null);
    if (res.ok) refresh();
  };

  return (
    <Screen title="Compras">
      <div className="px-5">
        <Card>
          <div className="flex items-start gap-3">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
              <CreditCard size={20} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">Tu tarjeta de negocio trabaja sola</p>
              <p className="text-xs text-muted">Cada compra entra a tus libros al instante. Solo te preguntamos cuando hay duda.</p>
            </div>
          </div>
          {spending.data && (
            <div className="mt-3 grid grid-cols-2 gap-3 border-t border-black/5 pt-3">
              <Stat label={`Compras ${spending.data.label}`} value={formatMoney(spending.data.total)} hint={`${spending.data.transaction_count} transacciones`} />
              <Stat label="Por confirmar" value={String(pending.length)} tone={pending.length ? "negative" : "neutral"} />
            </div>
          )}
          <Button variant="secondary" onClick={simulate} busy={simulating} className="mt-3 w-full">
            <Sparkles size={16} aria-hidden /> Simular compra con la tarjeta
          </Button>
          {simError && (
            <p className="mt-2 text-xs text-accent" role="alert">
              {simError}
            </p>
          )}
        </Card>
      </div>

      {purchases.loading && !purchases.data && <LoadingState label="Cargando compras…" />}
      {purchases.error && <ErrorState error={purchases.error} onRetry={purchases.reload} />}
      {purchases.data && list.length === 0 && <EmptyState title="Aún no hay compras" body="Cuando uses tu tarjeta de negocio, aparecerán aquí clasificadas automáticamente." />}

      {pending.length > 0 && (
        <section className="mt-6 px-5">
          <SectionTitle>¿Para qué fue esta compra?</SectionTitle>
          <ul className="space-y-3">
            {pending.map((tx) => (
              <li key={tx.transaction_id} className="rounded-2xl bg-white px-4 py-4 ring-1 ring-brand/20">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">{tx.merchant}</p>
                    <p className="text-xs text-muted">{formatDateTime(tx.occurred_at)}</p>
                  </div>
                  <span className="text-base font-semibold tabular-nums">{formatMoney(tx.amount)}</span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  Sugerencia: {tx.kind_label ?? "gasto"} ({Math.round((tx.confidence ?? 0) * 100)}% seguro). {tx.classification_reason}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {KIND_OPTIONS.map((opt) => (
                    <button
                      key={opt.kind}
                      type="button"
                      disabled={classifying === tx.transaction_id}
                      onClick={() => classify(tx, opt.kind)}
                      className={`rounded-xl px-3 py-2 text-left text-xs font-semibold ring-1 transition-colors ${tx.classification_kind === opt.kind ? "bg-brand/10 text-brand ring-brand/30" : "bg-tile text-ink ring-transparent"}`}
                    >
                      <span aria-hidden>{opt.emoji}</span> {opt.label}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {rest.length > 0 && (
        <section className="mt-6 px-5">
          <SectionTitle>Movimientos de la tarjeta</SectionTitle>
          <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white ring-1 ring-black/5">
            {rest.map((tx) => (
              <li key={tx.transaction_id} className="px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{tx.merchant}</p>
                    <p className="truncate text-[11px] text-muted">
                      {tx.kind_label ?? "—"}
                      {tx.account_name && tx.classification_kind !== "CARD_PAYMENT" && ` · ${tx.account_name}`} · {formatDateTime(tx.occurred_at)}
                    </p>
                  </div>
                  <span className={`text-sm font-semibold tabular-nums ${tx.direction === "CREDIT" ? "text-positive" : "text-ink"}`}>
                    {tx.direction === "CREDIT" ? "+" : "−"}
                    {formatMoney(tx.amount)}
                  </span>
                </div>
                {(tx.receipt || tx.sample_receipt_available) && (
                  <div className="mt-2 flex items-center gap-2">
                    {tx.receipt ? (
                      <StatusPill status="good" label={`Ticket: ${tx.receipt.items.length} artículos al inventario`} />
                    ) : (
                      <button type="button" onClick={() => setReceiptFor(tx)} className="inline-flex items-center gap-1 rounded-full bg-tile px-3 py-1 text-[11px] font-semibold">
                        <Receipt size={12} aria-hidden /> Agregar ticket
                      </button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <AnimatePresence>
        {receiptFor && (
          <ReceiptSheet
            api={api}
            tx={receiptFor}
            onClose={() => setReceiptFor(null)}
            onDone={() => {
              setReceiptFor(null);
              refresh();
            }}
          />
        )}
      </AnimatePresence>
    </Screen>
  );
}

/** Ticket: lo que un OCR extraería, emparejado con el inventario. */
function ReceiptSheet({ api, tx, onClose, onDone }: { api: BusinessApi; tx: CardTransaction; onClose: () => void; onDone: () => void }) {
  const [items, setItems] = useState<SampleReceiptItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.sampleReceipt(tx.transaction_id).then((res) => {
      if (res.ok) setItems(res.data);
      else setError(res.message);
    });
  }, [api, tx.transaction_id]);

  const apply = async () => {
    if (!items) return;
    setBusy(true);
    setError(null);
    const res = await api.attachReceipt(
      tx.transaction_id,
      items.map((i) => ({ ...i, create_inventory_item: !i.inventory_item_id })),
    );
    setBusy(false);
    if (!res.ok) {
      setError(res.message);
      return;
    }
    onDone();
  };

  const total = (items ?? []).reduce((s, i) => s + i.total_cost, 0);

  return (
    <BottomSheet label={`Ticket de ${tx.merchant}`} onDismiss={onClose}>
      <div className="flex items-center justify-between pt-2">
        <div>
          <h2 className="text-lg font-semibold">Ticket de {tx.merchant}</h2>
          <p className="text-xs text-muted">
            {formatDateTime(tx.occurred_at)} · {formatMoney(tx.amount)}
          </p>
        </div>
        <button type="button" onClick={onClose} aria-label="Cerrar" className="rounded-full p-1 text-muted">
          <X size={18} aria-hidden />
        </button>
      </div>
      <div className="mt-3">
        <Notice>Con el detalle del ticket, cada artículo entra a tu inventario con su cantidad y costo. Los que no existan se crean.</Notice>
      </div>
      {!items && !error && <LoadingState label="Leyendo el ticket…" />}
      {error && (
        <p className="mt-3 text-xs text-accent" role="alert">
          {error}
        </p>
      )}
      {items && (
        <ul className="mt-3 divide-y divide-black/5 rounded-2xl bg-tile/60 text-sm">
          {items.map((i, idx) => (
            <li key={idx} className="flex items-center justify-between px-3 py-2">
              <div className="min-w-0">
                <p className="truncate">{i.description}</p>
                <p className="text-[11px] text-muted">
                  {formatQty(i.quantity, i.unit)} × {formatMoney(i.unit_cost)} → {i.inventory_item_name ?? `nuevo: ${i.suggested_name}`}
                </p>
              </div>
              <span className="tabular-nums">{formatMoney(i.total_cost)}</span>
            </li>
          ))}
          <li className="flex justify-between px-3 py-2 font-semibold">
            <span>Total del ticket</span>
            <span className="tabular-nums">{formatMoney(total)}</span>
          </li>
        </ul>
      )}
      <div className="mt-4 flex gap-2">
        <Button variant="secondary" onClick={onClose} className="flex-1">
          Ahora no
        </Button>
        <Button onClick={apply} busy={busy} disabled={!items || items.length === 0} className="flex-1">
          <RefreshCw size={16} aria-hidden /> Aplicar al inventario
        </Button>
      </div>
    </BottomSheet>
  );
}
