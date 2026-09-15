import { useBusinessQuery } from "../business/useAsync";
import Screen from "../components/Screen";
import CashInsightCard from "../financial-literacy/CashInsightCard.jsx";
import MicroLessonDialog from "../financial-literacy/MicroLessonDialog.jsx";
import { pickSurveyTrigger } from "../financial-literacy/insights.js";

interface EducacionProps {
  profile: {
    category: string | null;
    answers: Record<string, boolean>;
  } | null;
}

/**
 * Educación contextual. Primero lo que disparan los DATOS reales del negocio
 * (liquidez baja, margen bajo, inventario atorado…), y después lo que
 * disparó la encuesta del onboarding, sin repetir un tema que los datos ya
 * cubren. Misma tarjeta, misma micro-lección.
 */
export default function Educacion({ profile }: EducacionProps) {
  const insights = useBusinessQuery((a) => a.insights());
  const shown = (insights.data ?? []).slice(0, 2);
  // Igual que en Cuenta: la lección de la encuesta depende de qué temas cubren
  // los datos, así que se espera la primera respuesta para no cambiarla después.
  const insightPending = insights.state.status === "loading" && !insights.data;

  return (
    <Screen>
      <MicroLessonDialog
        isOpen
        onClose={() => undefined}
        initialLesson={insights.data?.[0]?.lesson}
        profile={profile}
        embedded
      />

      {shown.map((insight) => (
        <CashInsightCard key={insight.id} profile={profile} trigger={{ ...insight, source: "data" }} />
      ))}

      {!insightPending && <CashInsightCard profile={profile} trigger={pickSurveyTrigger(profile, shown)} />}
    </Screen>
  );
}
