import Screen from "../components/Screen";
import CashInsightCard from "../financial-literacy/CashInsightCard.jsx";
import MicroLessonDialog from "../financial-literacy/MicroLessonDialog.jsx";

interface EducacionProps {
  profile: {
    category: string | null;
    answers: Record<string, boolean>;
  } | null;
}

export default function Educacion({ profile }: EducacionProps) {
  return (
    <Screen>
      <MicroLessonDialog
        isOpen
        onClose={() => undefined}
        initialLesson={undefined}
        profile={profile}
        embedded
      />

      <CashInsightCard profile={profile} />
    </Screen>
  );
}
