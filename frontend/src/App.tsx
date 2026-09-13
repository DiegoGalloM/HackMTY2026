import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { useState } from "react";
import BottomNav from "./components/BottomNav";
import Analisis from "./screens/Analisis";
import CobroEfectivo from "./screens/CobroEfectivo";
import Cuenta from "./screens/Cuenta";
import Educacion from "./screens/Educacion";
import Mas from "./screens/Mas";
import Pagos from "./screens/Pagos";
import Retiros from "./screens/Retiros";
import Transferencias from "./screens/Transferencias";
import PhoneFrame from "./onboarding/PhoneFrame.jsx";
import Onboarding from "./onboarding/Onboarding.jsx";
import Welcome from "./onboarding/Welcome";

interface BusinessProfile {
  category: string | null;
  answers: Record<string, boolean>;
}

function MainApp({ profile }: { profile: BusinessProfile | null }) {
  const location = useLocation();

  return (
    // w-full y NO `mx-auto max-w-md`: el ancho ya lo fija el mockup de celular
    // (.phone-frame__screen). Además ese contenedor es un flex column, y un
    // margen lateral `auto` en un flex item cancela el stretch del eje cruzado
    // — el shell se encogía a fit-content y quedaba centrado con huecos a los
    // lados, de ancho distinto en cada pantalla según su contenido.
    // El shell no scrollea; el scroll vive dentro de cada pantalla
    // (ver Screen.tsx), así la barra inferior nunca se mueve.
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-surface">
      {/* mode="wait" evita que dos pantallas se solapen durante la transición.
          La key es la ruta: sin ella AnimatePresence no detecta el cambio. */}
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Cuenta profile={profile} />} />
          <Route path="/retiros" element={<Retiros />} />
          <Route path="/transferencias" element={<Transferencias />} />
          <Route path="/analisis" element={<Analisis />} />
          <Route path="/cobro-efectivo" element={<CobroEfectivo />} />
          <Route path="/pagos" element={<Pagos />} />
          <Route path="/educacion" element={<Educacion profile={profile} />} />
          <Route path="/mas" element={<Mas />} />
          <Route path="*" element={<Cuenta profile={profile} />} />
        </Routes>
      </AnimatePresence>

      <BottomNav />
    </div>
  );
}

export default function App() {
  const [stage, setStage] = useState<"welcome" | "survey" | "account">("welcome");
  const [surveyStarted, setSurveyStarted] = useState(false);
  const [profile, setProfile] = useState<BusinessProfile | null>(null);

  // Un solo mockup de celular para toda la sesión: bienvenida, encuesta y app
  // principal viven dentro del mismo PhoneFrame, así el marco no se desmonta
  // ni cambia de tamaño al pasar de una etapa a otra.
  return (
    <PhoneFrame>
      {stage === "account" ? (
        <MainApp profile={profile} />
      ) : <>
        {stage === "welcome" && <Welcome
          onStart={() => { setSurveyStarted(true); setStage("survey"); }}
          onExplore={() => setStage("account")}
        />}
        {/* La encuesta se oculta (no se desmonta) para conservar las respuestas
            si el usuario vuelve a la bienvenida. */}
        {surveyStarted && <div className="phone-stage" hidden={stage !== "survey"}>
          <Onboarding
            active={stage === "survey"}
            onExit={() => setStage("welcome")}
            onComplete={(completedProfile?: BusinessProfile) => {
              setProfile(completedProfile ?? null);
              setStage("account");
            }}
          />
        </div>}
      </>}
    </PhoneFrame>
  );
}
