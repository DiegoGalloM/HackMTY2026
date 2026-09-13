import { useState } from "react";
import type { Insight } from "../api/types";
import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import CashInsightCard from "../financial-literacy/CashInsightCard.jsx";
import MicroLessonDialog from "../financial-literacy/MicroLessonDialog.jsx";

interface EducacionProps {
  profile: {
    category: string | null;
    answers: Record<string, boolean>;
  } | null;
}

/**
 * Educación contextual. Primero lo que disparan los DATOS reales del negocio
 * (liquidez baja, margen bajo, inventario atorado…), y después lo que
 * disparó la encuesta del onboarding. Misma tarjeta, misma micro-lección.
 */
export default function Educacion({ profile }: EducacionProps) {
  const insights = useBusinessQuery((a) => a.insights());

  return (
    <Screen>
      <MicroLessonDialog
        isOpen
        onClose={() => undefined}
        initialLesson={insights.data?.[0]?.lesson}
        profile={profile}
        embedded
      />

      {(insights.data ?? []).slice(0, 2).map((insight) => (
        <DataInsightCard key={insight.id} insight={insight} profile={profile} />
      ))}

      <CashInsightCard profile={profile} />
    </Screen>
  );
}

function DataInsightCard({ insight, profile }: { insight: Insight; profile: EducacionProps["profile"] }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="cash-insight-card" aria-labelledby={`data-insight-${insight.id}`}>
      <div className="cash-insight-card__icon" aria-hidden="true">
        📊
      </div>
      <div className="cash-insight-card__content">
        <p className="text-[11px] font-semibold tracking-wide text-accent uppercase">Según tus datos</p>
        <h2 id={`data-insight-${insight.id}`} className="cash-insight-card__title">
          {insight.title}
        </h2>
        <p className="cash-insight-card__body">{insight.body}</p>
        <button type="button" className="cash-insight-card__action" onClick={() => setOpen(true)}>
          {insight.action}
        </button>
      </div>
      <MicroLessonDialog isOpen={open} onClose={() => setOpen(false)} initialLesson={insight.lesson} profile={profile} />
    </section>
  );
}
