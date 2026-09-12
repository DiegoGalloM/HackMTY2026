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
  if (INVENTORY_TRIGGERS.has(trigger.id)) return "inventory";
  if (CASH_TRIGGERS.has(trigger.id)) return "cash";
  return "margin";
}

export default function CashInsightCard({ profile }) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const trigger = pickBestTrigger(profile);

  if (!trigger) return null;

  const suggestedLesson = getSuggestedLesson(trigger);

  return (
    <section className="cash-insight-card" aria-labelledby={`cash-insight-${trigger.id}`}>
      <div className="cash-insight-card__icon" aria-hidden="true">⚡</div>
      <div className="cash-insight-card__content">
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
