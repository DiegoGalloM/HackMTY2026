import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { ArrowDownToLine, ClipboardCheck, PackagePlus, X } from "lucide-react";
import type { BusinessApi } from "../api/finance";
import { formatDateTime, formatMoney, formatQty } from "../api/format";
import type { InventoryItem, InventoryMovement } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import BottomSheet from "../components/BottomSheet";
import Screen from "../components/Screen";
import { Button, Card, EmptyState, ErrorState, Field, LoadingState, NoSessionState, SectionTitle, Stat, StatusPill, inputClass } from "../components/ui";

const MOVEMENT_LABELS: Record<InventoryMovement["movement_type"], string> = {
  PURCHASE: "Compra",
  SALE_CONSUMPTION: "Venta",
  ADJUSTMENT: "Ajuste",
  WASTE: "Merma",
  INITIAL: "Inicial",
  REFUND: "Devolución",
};

type SheetState = { kind: "new" } | { kind: "receive"; item: InventoryItem } | { kind: "count"; item: InventoryItem } | null;

/** Inventario: existencias, valor a costo promedio y bitácora de movimientos. */
export default function Inventario() {
  const { api, refresh } = useBusiness();
  const summary = useBusinessQuery((a) => a.inventory());
  const movements = useBusinessQuery((a) => a.movements());
  const [sheet, setSheet] = useState<SheetState>(null);

  if (!api) {
    return (
      <Screen title="Inventario">
        <NoSessionState />
      </Screen>
    );
  }

  const items = summary.data?.items ?? [];

  return (
    <Screen title="Inventario">
      {summary.data && (
        <div className="px-5">
          <Card className="grid grid-cols-2 gap-3">
            <Stat label="Efectivo en inventario" value={formatMoney(summary.data.total_value)} hint="a costo promedio" />
            <Stat label="Insumos" value={String(summary.data.item_count)} hint={summary.data.low_stock_items.length ? `${summary.data.low_stock_items.length} por agotarse` : "todos con existencia"} tone={summary.data.low_stock_items.length ? "negative" : "neutral"} />
          </Card>
        </div>
      )}

      <div className="mt-6 px-5">
        <SectionTitle
          action={
            <button type="button" onClick={() => setSheet({ kind: "new" })} className="inline-flex items-center gap-1 text-xs font-semibold text-brand">
              <PackagePlus size={14} aria-hidden /> Agregar insumo
            </button>
          }
        >
          Existencias
        </SectionTitle>
      </div>
      {summary.loading && !summary.data && <LoadingState label="Cargando inventario…" />}
      {summary.error && <ErrorState error={summary.error} onRetry={summary.reload} />}
      {summary.data && items.length === 0 && (
        <EmptyState title="Sin insumos todavía" body="Registra lo que compras (harina, huevo, tinte…) y los productos lo descuentan solos al venderse." action={<Button onClick={() => setSheet({ kind: "new" })}>Agregar insumo</Button>} />
      )}
      <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white mx-5 ring-1 ring-black/5" aria-label="Insumos">
        {items.map((item) => (
          <li key={item.inventory_item_id} className="px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2 truncate text-sm font-semibold">
                  {item.name} {item.low_stock && <StatusPill status="attention" label="Por agotarse" />}
                </p>
                <p className="text-xs text-muted">
                  {formatQty(item.quantity_on_hand, item.unit_of_measure)} · {formatMoney(item.average_unit_cost)}/{item.unit_of_measure}
                  {item.reorder_point > 0 && ` · pedir en ${formatQty(item.reorder_point)}`}
                </p>
              </div>
              <span className="text-sm font-semibold tabular-nums">{formatMoney(item.inventory_value)}</span>
            </div>
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => setSheet({ kind: "receive", item })} className="inline-flex items-center gap-1 rounded-full bg-tile px-3 py-1 text-[11px] font-semibold">
                <ArrowDownToLine size={12} aria-hidden /> Registrar entrada
              </button>
              <button type="button" onClick={() => setSheet({ kind: "count", item })} className="inline-flex items-center gap-1 rounded-full bg-tile px-3 py-1 text-[11px] font-semibold">
                <ClipboardCheck size={12} aria-hidden /> Conteo
              </button>
            </div>
          </li>
        ))}
      </ul>

      <section className="mt-8 px-5">
        <SectionTitle>Movimientos recientes</SectionTitle>
        {movements.data && movements.data.length === 0 && <p className="text-xs text-muted">Aquí aparecerá cada entrada y salida, con su origen.</p>}
        <ul className="divide-y divide-black/5 overflow-hidden rounded-2xl bg-white ring-1 ring-black/5">
          {(movements.data ?? []).slice(0, 30).map((m) => (
            <li key={m.movement_id} className="flex items-center gap-3 px-4 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">
                  <span className="font-medium">{m.item_name}</span> <span className="text-muted">· {MOVEMENT_LABELS[m.movement_type] ?? m.movement_type}</span>
                </p>
                <p className="truncate text-[11px] text-muted">
                  {formatDateTime(m.occurred_at)}
                  {m.note && ` · ${m.note}`}
                </p>
              </div>
              <span className={`text-sm font-semibold tabular-nums ${m.quantity_delta > 0 ? "text-positive" : "text-ink"}`}>
                {m.quantity_delta > 0 ? "+" : ""}
                {formatQty(m.quantity_delta, m.unit_of_measure)}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <AnimatePresence>
        {sheet && (
          <InventorySheet
            key={sheet.kind + ("item" in sheet ? sheet.item.inventory_item_id : "")}
            api={api}
            sheet={sheet}
            onClose={() => setSheet(null)}
            onDone={() => {
              setSheet(null);
              refresh();
            }}
          />
        )}
      </AnimatePresence>
    </Screen>
  );
}

function InventorySheet({ api, sheet, onClose, onDone }: { api: BusinessApi; sheet: NonNullable<SheetState>; onClose: () => void; onDone: () => void }) {
  const [form, setForm] = useState({ name: "", unit: "unidad", quantity: "", cost: "", reorder: "", reason: "Conteo físico" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    let res;
    if (sheet.kind === "new") {
      if (!form.name.trim()) {
        setBusy(false);
        setError("Escribe el nombre del insumo.");
        return;
      }
      res = await api.createInventoryItem({
        name: form.name.trim(),
        unit_of_measure: form.unit.trim() || "unidad",
        initial_quantity: Number(form.quantity) || 0,
        initial_unit_cost: Number(form.cost) || 0,
        reorder_point: Number(form.reorder) || 0,
      });
    } else if (sheet.kind === "receive") {
      res = await api.receiveInventory(sheet.item.inventory_item_id, { quantity: Number(form.quantity), unit_cost: Number(form.cost) || 0 });
    } else {
      res = await api.countInventory(sheet.item.inventory_item_id, { counted_quantity: Number(form.quantity), reason: form.reason });
    }
    setBusy(false);
    if (!res.ok) {
      setError(res.message);
      return;
    }
    onDone();
  };

  const title = sheet.kind === "new" ? "Nuevo insumo" : sheet.kind === "receive" ? `Entrada de ${sheet.item.name}` : `Conteo de ${sheet.item.name}`;

  return (
    <BottomSheet label={title} onDismiss={onClose}>
      <div className="flex items-center justify-between pt-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Cerrar" className="rounded-full p-1 text-muted">
          <X size={18} aria-hidden />
        </button>
      </div>
      <div className="mt-3 space-y-3">
        {sheet.kind === "new" && (
          <>
            <Field label="Nombre">
              <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej. Harina de trigo" />
            </Field>
            <Field label="Unidad de medida">
              <input className={inputClass} value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="kg, l, pieza" />
            </Field>
          </>
        )}
        {sheet.kind === "count" ? (
          <>
            <p className="text-xs text-muted">
              El sistema tiene {formatQty(sheet.item.quantity_on_hand, sheet.item.unit_of_measure)}. Escribe lo que contaste; la diferencia se registra como merma o sobrante.
            </p>
            <Field label={`Cantidad contada (${sheet.item.unit_of_measure})`}>
              <input className={inputClass} inputMode="decimal" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
            </Field>
            <Field label="Motivo">
              <input className={inputClass} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
            </Field>
          </>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <Field label={sheet.kind === "new" ? "Cantidad inicial" : "Cantidad recibida"}>
              <input className={inputClass} inputMode="decimal" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} placeholder="0" />
            </Field>
            <Field label="Costo por unidad">
              <input className={inputClass} inputMode="decimal" value={form.cost} onChange={(e) => setForm({ ...form, cost: e.target.value })} placeholder="0.00" />
            </Field>
          </div>
        )}
        {sheet.kind === "new" && (
          <Field label="Avisarme cuando queden (punto de reorden)" hint="Opcional. Si conoces cuánto tarda tu proveedor, pon lo que consumes en ese tiempo.">
            <input className={inputClass} inputMode="decimal" value={form.reorder} onChange={(e) => setForm({ ...form, reorder: e.target.value })} placeholder="0" />
          </Field>
        )}
        {error && (
          <p className="text-xs text-accent" role="alert">
            {error}
          </p>
        )}
        <Button onClick={submit} busy={busy} className="w-full">
          Guardar
        </Button>
      </div>
    </BottomSheet>
  );
}
