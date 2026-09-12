import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { useState } from "react";
import BottomNav from "./components/BottomNav";
import Cuenta from "./screens/Cuenta";
import Mas from "./screens/Mas";
import Pagos from "./screens/Pagos";
import Retiros from "./screens/Retiros";
import Transferencias from "./screens/Transferencias";
import PhoneFrame from "./onboarding/PhoneFrame.jsx";
import Logo from "./onboarding/Logo.jsx";
import Onboarding from "./onboarding/Onboarding.jsx";

interface BusinessProfile {
  category: string | null;
  answers: Record<string, boolean>;
}

function MainApp({ profile }: { profile: BusinessProfile | null }) {
  const location = useLocation();

  return (
    // El shell ocupa 100dvh y no scrollea; el scroll vive dentro de cada
    // pantalla (ver Screen.tsx), así la barra inferior nunca se mueve.
    <div className="relative mx-auto flex h-full max-w-md flex-col overflow-hidden bg-surface">
      {/* mode="wait" evita que dos pantallas se solapen durante la transición.
          La key es la ruta: sin ella AnimatePresence no detecta el cambio. */}
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Cuenta profile={profile} />} />
          <Route path="/retiros" element={<Retiros />} />
          <Route path="/transferencias" element={<Transferencias />} />
          <Route path="/pagos" element={<Pagos />} />
          <Route path="/mas" element={<Mas />} />
          <Route path="*" element={<Cuenta profile={profile} />} />
        </Routes>
      </AnimatePresence>

      <BottomNav />
    </div>
  );
}

export default function App() {
  // Encuesta de onboarding primero; al terminar (o si el usuario decide
  // seguir tras un error de guardado) se muestra la app principal, ambas
  // dentro del mismo mockup de celular (PhoneFrame).
  const [onboardingDone, setOnboardingDone] = useState(false);
  const [profile, setProfile] = useState<BusinessProfile | null>(null);

  return (
    <PhoneFrame>
      {onboardingDone ? (
        <MainApp profile={profile} />
      ) : (
        <>
          <Logo />
          <Onboarding
            onComplete={(completedProfile: BusinessProfile) => {
              setProfile(completedProfile);
              setOnboardingDone(true);
            }}
          />
        </>
      )}
    </PhoneFrame>
  );
}
