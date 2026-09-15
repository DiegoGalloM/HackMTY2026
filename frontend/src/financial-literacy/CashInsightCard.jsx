import { useState } from "react";
import MicroLessonDialog from "./MicroLessonDialog.jsx";
import { pickBestTrigger } from "./insights.js";

const INVENTORY_TRIGGERS = new Set([
  "stockout_y_sobrecompra",
  "stockout",
  "sobrecompra",
  "guarda_inventario",
  "compra_mayoreo",
  "categoria_retail",
]);

const CASH_TRIGGERS = new Set(["categoria_servicios", "categoria_construccion"]);

function getSuggestedLesson(trigger) {
  // Los insights de datos ya traen su lección desde el backend.
  if (trigger.lesson) return trigger.lesson;
  if (INVENTORY_TRIGGERS.has(trigger.id)) return "inventory";
  if (CASH_TRIGGERS.has(trigger.id)) return "cash";
  return "margin";
}

/**
 * Tarjeta de Cash Insight. Recibe el `trigger` ya elegido o, si no, lo elige
 * con la prioridad de insights.js: insight de datos primero, encuesta después.
 *
 * @param {{ profile?: any, dataInsights?: Array<{ id: string }>, trigger?: any }} props
 */
export default function CashInsightCard({ profile, dataInsights = [], trigger: chosen }) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const trigger = chosen === undefined ? pickBestTrigger(profile, dataInsights) : chosen;

  if (!trigger) return null;

  const suggestedLesson = getSuggestedLesson(trigger);
  const fromData = trigger.source === "data";

  return (
    <section
      className="cash-insight-card"
      aria-labelledby={`cash-insight-${trigger.id}`}
      data-insight-source={fromData ? "data" : "survey"}
    >
      <div className="cash-insight-card__icon" aria-hidden="true">{fromData ? "📊" : "⚡"}</div>
      <div className="cash-insight-card__content">
        {fromData && <p className="text-[11px] font-semibold tracking-wide text-accent uppercase">Según tus datos</p>}
        <h2 id={`cash-insight-${trigger.id}`} className="cash-insight-card__title">
          {trigger.title}
        </h2>
        <p className="cash-insight-card__body">{trigger.body}</p>
        <button
          type="button"
          className="cash-insight-card__action"
          onClick={() => setIsDialogOpen(true)}
        >
          {trigger.action}
        </button>
      </div>
      <MicroLessonDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        initialLesson={suggestedLesson}
        profile={profile}
      />
    </section>
  );
}
