import { useEffect, useState } from "react";
import { BarChart3, ChevronLeft, PackageCheck, WalletCards, X } from "lucide-react";

const LESSONS = [
  {
    id: "cash",
    icon: WalletCards,
    title: "Mi caja esta semana",
    description: "Mira si lo que entra alcanza para tus próximos pagos.",
  },
  {
    id: "margin",
    icon: BarChart3,
    title: "Lo que deja una venta",
    description: "Calcula lo que realmente te queda por cada venta.",
  },
  {
    id: "inventory",
    icon: PackageCheck,
    title: "Mi inventario",
    description: "Decide qué reordenar y qué dejar de comprar por ahora.",
  },
];

const formatCurrency = (amount) => new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 0,
}).format(amount);

const toAmount = (value) => Number(value) || 0;

function getSaleName(category) {
  if (category === "comida") return "platillo";
  if (category === "belleza" || category === "servicios") return "servicio";
  if (category === "transporte") return "viaje";
  return "venta";
}

function getInventoryName(category) {
  if (category === "comida") return "ingrediente";
  if (category === "construccion") return "material";
  return "producto";
}

export default function MicroLessonDialog({ isOpen, onClose, initialLesson, profile, embedded = false }) {
  const [selectedLesson, setSelectedLesson] = useState(initialLesson ?? null);
  const [cash, setCash] = useState({ available: "", incoming: "", expenses: "" });
  const [margin, setMargin] = useState({ price: "", cost: "" });
  const [inventory, setInventory] = useState({ item: "", movement: "", stockValue: "" });

  useEffect(() => {
    if (isOpen) setSelectedLesson(initialLesson ?? null);
  }, [initialLesson, isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;

    const closeOnEscape = (event) => {
      if (event.key === "Escape") onClose();
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const saleName = getSaleName(profile?.category);
  const inventoryName = getInventoryName(profile?.category);
  const showLessonPicker = () => setSelectedLesson(null);

  if (embedded) {
    return (
      <section className="micro-lessons-page" aria-labelledby="micro-lessons-title">
        {!selectedLesson ? (
          <LessonPicker initialLesson={initialLesson} onSelect={setSelectedLesson} page />
        ) : (
          <>
            <button
              type="button"
              className="micro-lessons-page__back"
              onClick={showLessonPicker}
            >
              <ChevronLeft size={20} aria-hidden="true" />
              Volver a lecciones
            </button>
            <LessonContent
              lesson={selectedLesson}
              saleName={saleName}
              inventoryName={inventoryName}
              cash={cash}
              margin={margin}
              inventory={inventory}
              setCash={setCash}
              setMargin={setMargin}
              setInventory={setInventory}
              onClose={showLessonPicker}
            />
          </>
        )}
      </section>
    );
  }

  return (
    <div className="micro-lessons-overlay">
      <section className="micro-lessons-dialog" role="dialog" aria-modal="true" aria-labelledby="micro-lessons-title">
        <header className="micro-lessons-dialog__header">
          {selectedLesson ? (
            <button type="button" className="micro-lessons-icon-button" onClick={() => setSelectedLesson(null)} aria-label="Ver las tres lecciones">
              <ChevronLeft size={22} aria-hidden="true" />
            </button>
          ) : <span className="micro-lessons-dialog__spacer" />}
          <p className="micro-lessons-dialog__time">Menos de 1 minuto</p>
          <button type="button" className="micro-lessons-icon-button" onClick={onClose} aria-label="Cerrar lecciones">
            <X size={22} aria-hidden="true" />
          </button>
        </header>

        {!selectedLesson ? (
          <LessonPicker initialLesson={initialLesson} onSelect={setSelectedLesson} />
        ) : (
          <LessonContent
            lesson={selectedLesson}
            saleName={saleName}
            inventoryName={inventoryName}
            cash={cash}
            margin={margin}
            inventory={inventory}
            setCash={setCash}
            setMargin={setMargin}
            setInventory={setInventory}
            onClose={onClose}
          />
        )}
      </section>
    </div>
  );
}

function LessonPicker({ initialLesson, onSelect, page = false }) {
  const Title = page ? "h1" : "h2";

  return (
    <div className="micro-lessons-dialog__body">
      <p className="micro-lessons-eyebrow">Aprende para tu negocio</p>
      <Title id="micro-lessons-title" className="micro-lessons-title">Elige una decisión para hoy</Title>
      <p className="micro-lessons-intro">Responde solo lo esencial y recibe una guía clara.</p>
      <div className="micro-lessons-list">
        {LESSONS.map(({ id, icon: Icon, title, description }) => (
          <button type="button" className="micro-lessons-option" key={id} onClick={() => onSelect(id)}>
            <Icon size={22} aria-hidden="true" />
            <span>
              <strong>{title}</strong>
              <small>{description}</small>
              {initialLesson === id && <em>Recomendada para ti</em>}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function LessonContent({ lesson, saleName, inventoryName, cash, margin, inventory, setCash, setMargin, setInventory, onClose }) {
  if (lesson === "cash") {
    const complete = Object.values(cash).every((value) => value !== "");
    const closingCash = toAmount(cash.available) + toAmount(cash.incoming) - toAmount(cash.expenses);

    return (
      <div className="micro-lessons-dialog__body">
        <p className="micro-lessons-eyebrow">Caja de los próximos 7 días</p>
        <h2 id="micro-lessons-title" className="micro-lessons-title">¿Te alcanza para esta semana?</h2>
        <p className="micro-lessons-intro">Usa cantidades aproximadas. No necesitas revisar toda tu contabilidad.</p>
        <AmountField label="Efectivo que tienes hoy" value={cash.available} onChange={(available) => setCash({ ...cash, available })} />
        <AmountField label="Dinero que esperas recibir" value={cash.incoming} onChange={(incoming) => setCash({ ...cash, incoming })} />
        <AmountField label="Pagos que debes hacer" value={cash.expenses} onChange={(expenses) => setCash({ ...cash, expenses })} />
        {complete && <CashResult closingCash={closingCash} onClose={onClose} />}
      </div>
    );
  }

  if (lesson === "margin") {
    const complete = margin.price !== "" && margin.cost !== "";
    const profit = toAmount(margin.price) - toAmount(margin.cost);
    const marginPercent = toAmount(margin.price) > 0 ? (profit / toAmount(margin.price)) * 100 : 0;

    return (
      <div className="micro-lessons-dialog__body">
        <p className="micro-lessons-eyebrow">Margen por {saleName}</p>
        <h2 id="micro-lessons-title" className="micro-lessons-title">¿Qué te queda por cada {saleName}?</h2>
        <p className="micro-lessons-intro">Solo cuenta lo que gastas directamente para hacer o comprar este {saleName}.</p>
        <AmountField label={`¿En cuánto vendes este ${saleName}?`} value={margin.price} onChange={(price) => setMargin({ ...margin, price })} />
        <AmountField label={`¿Cuánto te cuesta esta ${saleName}?`} value={margin.cost} onChange={(cost) => setMargin({ ...margin, cost })} />
        {complete && <MarginResult profit={profit} marginPercent={marginPercent} saleName={saleName} onClose={onClose} />}
      </div>
    );
  }

  const hasMovement = inventory.movement !== "";
  const item = inventory.item.trim() || `este ${inventoryName}`;
  const stockValue = toAmount(inventory.stockValue);
  const result = {
    fast: { title: "Vas por buen camino", body: `${item} se mueve rápido. Antes de que se termine, anota cuánto tarda tu proveedor en entregarlo y compra con ese tiempo de anticipación.` },
    normal: { title: "Mantén la mirada en este producto", body: `${item} tiene un ritmo sano. Revisa otra vez la próxima semana antes de aumentar tu compra.` },
    slow: { title: "Aquí puede haber efectivo atrapado", body: `${item} lleva tiempo sin moverse. Por ahora evita comprar más y prueba ofrecerlo junto con algo que sí se venda.` },
  }[inventory.movement];

  return (
    <div className="micro-lessons-dialog__body">
      <p className="micro-lessons-eyebrow">Inventario simple</p>
      <h2 id="micro-lessons-title" className="micro-lessons-title">¿Cómo se está moviendo tu inventario?</h2>
      <p className="micro-lessons-intro">Elige un {inventoryName} importante. No hace falta contar todo tu negocio.</p>
      <label className="micro-lessons-field">
        <span>¿Qué {inventoryName} quieres revisar?</span>
        <input value={inventory.item} onChange={(event) => setInventory({ ...inventory, item: event.target.value })} placeholder={`Ej. mi ${inventoryName} más vendido`} />
      </label>
      <fieldset className="micro-lessons-choice-group">
        <legend>En la última semana…</legend>
        <div>
          <Choice label="Se acaba rápido" value="fast" selected={inventory.movement} onChange={(movement) => setInventory({ ...inventory, movement })} />
          <Choice label="Se vende normal" value="normal" selected={inventory.movement} onChange={(movement) => setInventory({ ...inventory, movement })} />
          <Choice label="Lleva semanas sin moverse" value="slow" selected={inventory.movement} onChange={(movement) => setInventory({ ...inventory, movement })} />
        </div>
      </fieldset>
      <AmountField label={`Opcional: ¿cuánto pagaste por lo que te queda de ${inventoryName}?`} value={inventory.stockValue} onChange={(stockValue) => setInventory({ ...inventory, stockValue })} />
      {hasMovement && <InventoryResult result={result} stockValue={stockValue} onClose={onClose} />}
    </div>
  );
}

function AmountField({ label, value, onChange }) {
  return (
    <label className="micro-lessons-field">
      <span>{label}</span>
      <div className="micro-lessons-money-input">
        <span>$</span>
        <input type="number" min="0" inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)} placeholder="0" />
      </div>
    </label>
  );
}

function Choice({ label, value, selected, onChange }) {
  return <button type="button" className={`micro-lessons-choice ${selected === value ? "micro-lessons-choice--selected" : ""}`} onClick={() => onChange(value)}>{label}</button>;
}

function CashResult({ closingCash, onClose }) {
  const isShort = closingCash < 0;
  return (
    <ResultCard title={isShort ? "Hay una brecha que puedes anticipar" : "Tu semana cierra con efectivo disponible"} onClose={onClose}>
      <strong className={isShort ? "micro-lessons-result__amount micro-lessons-result__amount--alert" : "micro-lessons-result__amount"}>{formatCurrency(Math.abs(closingCash))}</strong>
      <p>{isShort ? "te faltarían después de tus pagos. Prioriza un cobro pendiente o mueve una compra que pueda esperar." : "te quedarían después de tus pagos. Aparta una parte antes de hacer una compra extra."}</p>
    </ResultCard>
  );
}

function MarginResult({ profit, marginPercent, saleName, onClose }) {
  const isLoss = profit <= 0;
  return (
    <ResultCard title={isLoss ? "Este precio no cubre su costo directo" : `Esto deja cada ${saleName}`} onClose={onClose}>
      <strong className={isLoss ? "micro-lessons-result__amount micro-lessons-result__amount--alert" : "micro-lessons-result__amount"}>{formatCurrency(Math.abs(profit))}</strong>
      <p>{isLoss ? "de diferencia. Revisa el costo o el precio antes de volver a ofrecerlo." : `antes de renta, sueldos y otros gastos fijos. Eso equivale a un margen aproximado de ${Math.round(marginPercent)}%.`}</p>
    </ResultCard>
  );
}

function InventoryResult({ result, stockValue, onClose }) {
  return (
    <ResultCard title={result.title} onClose={onClose}>
      <p>{result.body}</p>
      {stockValue > 0 && <p><strong>{formatCurrency(stockValue)}</strong> es efectivo que hoy está en inventario.</p>}
    </ResultCard>
  );
}

function ResultCard({ title, children, onClose }) {
  return (
    <section className="micro-lessons-result" aria-live="polite">
      <p className="micro-lessons-result__label">Tu resultado</p>
      <h3>{title}</h3>
      {children}
      <button type="button" className="micro-lessons-primary-button" onClick={onClose}>Listo por hoy</button>
    </section>
  );
}
