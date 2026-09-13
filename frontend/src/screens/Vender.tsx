import { useEffect, useMemo, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { QRCodeSVG } from "qrcode.react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, ExternalLink, Minus, PackagePlus, Plus, QrCode, X } from "lucide-react";
import { checkoutUrl } from "../api/config";
import { payCheckout, type BusinessApi } from "../api/finance";
import { formatMoney, formatPct } from "../api/format";
import type { InventoryItem, Order, SellableItemInput } from "../api/types";
import { useBusiness } from "../business/BusinessContext";
import { useBusinessQuery } from "../business/useAsync";
import BottomSheet from "../components/BottomSheet";
import Screen from "../components/Screen";
import { Button, EmptyState, ErrorState, Field, LoadingState, NoSessionState, Notice, SectionTitle, inputClass } from "../components/ui";

type Cart = Record<string, number>;

/**
 * Vender: elige productos ya configurados, genera el QR de ESA orden y espera
 * el pago. Nada se registra hasta que el pago se confirma en el backend.
 */
export default function Vender() {
  const { api, refresh } = useBusiness();
  const catalog = useBusinessQuery((a) => a.catalog());
  const [cart, setCart] = useState<Cart>({});
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [newItem, setNewItem] = useState(false);

  const items = catalog.data ?? [];
  const byId = useMemo(() => Object.fromEntries(items.map((i) => [i.item_id, i])), [items]);
  const lines = Object.entries(cart).filter(([, q]) => q > 0);
  const subtotal = lines.reduce((s, [id, q]) => s + (byId[id]?.selling_price ?? 0) * q, 0);
  const tax = lines.reduce((s, [id, q]) => s + (byId[id]?.selling_price ?? 0) * q * (byId[id]?.tax_rate ?? 0), 0);
  const total = subtotal + tax;

  const change = (id: string, delta: number) =>
    setCart((prev) => {
      const next = { ...prev, [id]: Math.max(0, (prev[id] ?? 0) + delta) };
      if (next[id] === 0) delete next[id];
      return next;
    });

  const createOrder = async () => {
    if (!api || lines.length === 0) return;
    setCreating(true);
    setCreateError(null);
    const res = await api.createOrder(lines.map(([item_id, quantity]) => ({ item_id, quantity })));
    setCreating(false);
    if (!res.ok) {
      setCreateError(res.message);
      return;
    }
    setOrder(res.data);
  };

  if (!api) {
    return (
      <Screen title="Vender">
        <NoSessionState />
      </Screen>
    );
  }

  return (
    <Screen title="Vender">
      <div className="px-5">
        <SectionTitle
          action={
            <button type="button" onClick={() => setNewItem(true)} className="inline-flex items-center gap-1 text-xs font-semibold text-brand">
              <PackagePlus size={14} aria-hidden /> Nuevo producto
            </button>
          }
        >
          Tus productos y servicios
        </SectionTitle>
      </div>

      {catalog.loading && !catalog.data && <LoadingState label="Cargando catálogo…" />}
      {catalog.error && <ErrorState error={catalog.error} onRetry={catalog.reload} />}
      {catalog.data && items.length === 0 && (
        <EmptyState
          title="Todavía no tienes productos"
          body="Configura una vez lo que vendes (precio y receta) y después cobra en dos toques."
          action={<Button onClick={() => setNewItem(true)}>Crear mi primer producto</Button>}
        />
      )}

      <ul className="space-y-2 px-5" aria-label="Catálogo">
        {items.map((item) => {
          const qty = cart[item.item_id] ?? 0;
          const soldOut = item.producible_units !== null && item.producible_units <= 0;
          return (
            <li key={item.item_id} className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 ring-1 ring-black/5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-tile text-xl" aria-hidden>
                {item.emoji || (item.item_type === "SERVICE" ? "🛠️" : "🛍️")}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{item.name}</p>
                <p className="text-xs text-muted">
                  {formatMoney(item.selling_price)}
                  {item.tax_rate > 0 && ` + ${formatPct(item.tax_rate * 100, 2)} imp.`}
                  {item.producible_units !== null && (
                    <span className={soldOut ? " text-accent" : ""}>{` · ${soldOut ? "sin insumos" : `${item.producible_units} disponibles`}`}</span>
                  )}
                </p>
              </div>
              {qty === 0 ? (
                <button type="button" onClick={() => change(item.item_id, 1)} aria-label={`Agregar ${item.name}`} className="flex size-9 items-center justify-center rounded-full bg-brand text-white active:scale-95">
                  <Plus size={18} aria-hidden />
                </button>
              ) : (
                <div className="flex items-center gap-1 rounded-full bg-tile px-1">
                  <button type="button" onClick={() => change(item.item_id, -1)} aria-label={`Quitar ${item.name}`} className="flex size-8 items-center justify-center rounded-full">
                    <Minus size={16} aria-hidden />
                  </button>
                  <span className="w-5 text-center text-sm font-semibold tabular-nums">{qty}</span>
                  <button type="button" onClick={() => change(item.item_id, 1)} aria-label={`Agregar otro ${item.name}`} className="flex size-8 items-center justify-center rounded-full">
                    <Plus size={16} aria-hidden />
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {lines.length > 0 && (
        <div className="mx-5 mt-5 rounded-2xl bg-white px-4 py-4 ring-1 ring-black/5">
          <div className="flex justify-between text-sm">
            <span className="text-muted">Subtotal</span>
            <span className="tabular-nums">{formatMoney(subtotal)}</span>
          </div>
          {tax > 0 && (
            <div className="mt-1 flex justify-between text-sm">
              <span className="text-muted">Impuesto sobre ventas</span>
              <span className="tabular-nums">{formatMoney(tax)}</span>
            </div>
          )}
          <div className="mt-2 flex justify-between border-t border-black/5 pt-2 text-base font-semibold">
            <span>Total</span>
            <span className="tabular-nums">{formatMoney(total)}</span>
          </div>
          {createError && (
            <p className="mt-2 text-xs text-accent" role="alert">
              {createError}
            </p>
          )}
          <Button onClick={createOrder} busy={creating} className="mt-4 w-full">
            <QrCode size={18} aria-hidden /> Generar QR para cobrar {formatMoney(total)}
          </Button>
          <button type="button" onClick={() => setCart({})} className="mt-2 w-full text-xs text-muted">
            Vaciar
          </button>
        </div>
      )}

      <AnimatePresence>
        {order && (
          <OrderSheet
            key={order.order_id}
            api={api}
            order={order}
            onClose={() => setOrder(null)}
            onPaid={() => {
              setCart({});
              refresh();
            }}
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {newItem && (
          <NewItemSheet
            api={api}
            onClose={() => setNewItem(false)}
            onCreated={() => {
              setNewItem(false);
              catalog.reload();
            }}
          />
        )}
      </AnimatePresence>
    </Screen>
  );
}

// -------------------------------------------------------------- QR + pago --

function OrderSheet({ api, order: initial, onClose, onPaid }: { api: BusinessApi; order: Order; onClose: () => void; onPaid: () => void }) {
  const [order, setOrder] = useState(initial);
  const [simulating, setSimulating] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const navigate = useNavigate();
  const url = checkoutUrl(order.checkout_token);
  const paid = order.status === "PAID";

  // El vendedor ve el pago llegar solo: se consulta la orden cada 2 s hasta
  // que el backend la marque pagada (el evento autoritativo vive allá).
  useEffect(() => {
    if (paid) return;
    const timer = window.setInterval(async () => {
      const res = await api.order(order.order_id);
      if (res.ok && res.data.status !== order.status) setOrder(res.data);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [api, order.order_id, order.status, paid]);

  useEffect(() => {
    if (paid) onPaid();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paid]);

  const cogs = order.lines.reduce((s, l) => s + (l.unit_cost ?? 0) * l.quantity, 0);
  const grossProfit = order.subtotal - cogs;

  const simulate = async () => {
    setSimulating(true);
    setSimError(null);
    // Mismo camino que el cliente real: la página pública de pago.
    const res = await payCheckout(order.checkout_token, { card_last4: "4242" });
    setSimulating(false);
    if (!res.ok) {
      setSimError(res.message);
      return;
    }
    const fresh = await api.order(order.order_id);
    if (fresh.ok) setOrder(fresh.data);
  };

  return (
    <BottomSheet label={paid ? "Pago recibido" : `Cobro de la orden ${order.order_number}`} onDismiss={onClose}>
      <div className="flex items-center justify-between pt-2">
        <p className="text-xs font-semibold text-muted">Orden #{order.order_number}</p>
        <button type="button" onClick={onClose} aria-label="Cerrar" className="rounded-full p-1 text-muted">
          <X size={18} aria-hidden />
        </button>
      </div>

      {paid ? (
        <div className="py-4 text-center">
          <CheckCircle2 size={44} className="mx-auto text-positive" aria-hidden />
          <h2 className="mt-2 text-xl font-semibold">Pago recibido</h2>
          <p className="mt-1 text-3xl font-semibold tabular-nums">{formatMoney(order.total)}</p>
          {order.payment?.card_last4 && <p className="text-xs text-muted">Tarjeta terminada en {order.payment.card_last4}</p>}
          <div className="mt-4 space-y-2 text-left">
            <Notice tone="success">Vendiste {formatMoney(order.subtotal)}. Tu ganancia estimada fue {formatMoney(grossProfit)}.</Notice>
            {cogs > 0 && <Notice>Inventario actualizado automáticamente ({formatMoney(cogs)} en insumos).</Notice>}
            {order.tax_total > 0 && <Notice>{formatMoney(order.tax_total)} de impuesto quedaron apartados para el estado.</Notice>}
            <Notice>Libros, estados financieros y análisis ya reflejan esta venta.</Notice>
          </div>
          <div className="mt-4 flex gap-2">
            <Button variant="secondary" onClick={onClose} className="flex-1">
              Nueva venta
            </Button>
            <Button onClick={() => navigate("/analisis")} className="flex-1">
              Ver análisis
            </Button>
          </div>
        </div>
      ) : (
        <div className="py-3 text-center">
          <p className="text-sm text-muted">El cliente escanea y paga {formatMoney(order.total)}</p>
          <div className="mx-auto mt-3 w-fit rounded-2xl bg-white p-3 ring-1 ring-black/10">
            <QRCodeSVG value={url} size={196} level="M" includeMargin={false} aria-label="Código QR de pago" />
          </div>
          <ul className="mx-auto mt-3 max-w-xs text-left text-xs text-muted">
            {order.lines.map((l) => (
              <li key={l.order_line_id} className="flex justify-between">
                <span>
                  {l.quantity} × {l.item_name}
                </span>
                <span className="tabular-nums">{formatMoney(l.line_subtotal)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted" role="status">
            Esperando el pago… la pantalla se actualiza sola.
          </p>
          {simError && (
            <p className="mt-2 text-xs text-accent" role="alert">
              {simError}
            </p>
          )}
          <div className="mt-4 flex gap-2">
            <a href={url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 flex-1 items-center justify-center gap-1 rounded-full bg-tile text-sm font-semibold">
              <ExternalLink size={16} aria-hidden /> Abrir como cliente
            </a>
            <Button onClick={simulate} busy={simulating} className="flex-1">
              Simular pago
            </Button>
          </div>
          <button type="button" onClick={async () => { await api.cancelOrder(order.order_id); onClose(); }} className="mt-3 text-xs text-muted underline">
            Cancelar esta orden
          </button>
        </div>
      )}
    </BottomSheet>
  );
}

// ------------------------------------------------------- nuevo producto --

function NewItemSheet({ api, onClose, onCreated }: { api: BusinessApi; onClose: () => void; onCreated: () => void }) {
  const inventory = useBusinessQuery((a) => a.inventory());
  const [form, setForm] = useState({ name: "", item_type: "PRODUCT" as "PRODUCT" | "SERVICE", price: "", tax: "8.25", emoji: "" });
  const [components, setComponents] = useState<{ inventory_item_id: string; quantity_per_unit: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const invItems: InventoryItem[] = inventory.data?.items ?? [];

  const submit = async () => {
    const price = Number(form.price);
    if (!form.name.trim() || !(price >= 0)) {
      setError("Escribe el nombre y un precio válido.");
      return;
    }
    const payload: SellableItemInput = {
      name: form.name.trim(),
      item_type: form.item_type,
      selling_price: price,
      tax_rate: Math.max(0, Number(form.tax) || 0) / 100,
      emoji: form.emoji.trim(),
      components: components.filter((c) => c.inventory_item_id && Number(c.quantity_per_unit) > 0).map((c) => ({ inventory_item_id: c.inventory_item_id, quantity_per_unit: Number(c.quantity_per_unit) })),
    };
    setBusy(true);
    setError(null);
    const res = await api.createCatalogItem(payload);
    setBusy(false);
    if (!res.ok) {
      setError(res.message);
      return;
    }
    onCreated();
  };

  return (
    <BottomSheet label="Nuevo producto o servicio" onDismiss={onClose}>
      <h2 className="pt-2 text-lg font-semibold">Nuevo producto o servicio</h2>
      <p className="text-xs text-muted">Se configura una vez; cada venta descuenta su receta del inventario sola.</p>
      <div className="mt-3 space-y-3">
        <div className="flex rounded-full bg-tile p-1">
          {(["PRODUCT", "SERVICE"] as const).map((t) => (
            <button key={t} type="button" onClick={() => setForm({ ...form, item_type: t })} aria-pressed={form.item_type === t} className={`flex-1 rounded-full py-1.5 text-xs font-semibold ${form.item_type === t ? "bg-white text-brand shadow-sm" : "text-muted"}`}>
              {t === "PRODUCT" ? "Producto" : "Servicio"}
            </button>
          ))}
        </div>
        <Field label="Nombre">
          <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ej. Pastel de chocolate" />
        </Field>
        <div className="grid grid-cols-3 gap-2">
          <Field label="Precio (USD)">
            <input className={inputClass} inputMode="decimal" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="25" />
          </Field>
          <Field label="Impuesto %">
            <input className={inputClass} inputMode="decimal" value={form.tax} onChange={(e) => setForm({ ...form, tax: e.target.value })} />
          </Field>
          <Field label="Emoji">
            <input className={inputClass} value={form.emoji} onChange={(e) => setForm({ ...form, emoji: e.target.value })} placeholder="🎂" />
          </Field>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-muted">Receta (insumos por unidad)</span>
            <button type="button" onClick={() => setComponents([...components, { inventory_item_id: invItems[0]?.inventory_item_id ?? "", quantity_per_unit: "" }])} className="text-xs font-semibold text-brand" disabled={invItems.length === 0}>
              + Agregar insumo
            </button>
          </div>
          {invItems.length === 0 && <p className="text-[11px] text-muted">Primero registra insumos en Inventario para armar la receta (opcional).</p>}
          {components.map((c, i) => (
            <div key={i} className="mb-2 flex gap-2">
              <select className={inputClass} value={c.inventory_item_id} onChange={(e) => setComponents(components.map((x, j) => (j === i ? { ...x, inventory_item_id: e.target.value } : x)))}>
                {invItems.map((it) => (
                  <option key={it.inventory_item_id} value={it.inventory_item_id}>
                    {it.name} ({it.unit_of_measure})
                  </option>
                ))}
              </select>
              <input className={`${inputClass} w-24`} inputMode="decimal" placeholder="cant." value={c.quantity_per_unit} onChange={(e) => setComponents(components.map((x, j) => (j === i ? { ...x, quantity_per_unit: e.target.value } : x)))} />
              <button type="button" aria-label="Quitar insumo" onClick={() => setComponents(components.filter((_, j) => j !== i))} className="text-muted">
                <X size={16} aria-hidden />
              </button>
            </div>
          ))}
        </div>
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
