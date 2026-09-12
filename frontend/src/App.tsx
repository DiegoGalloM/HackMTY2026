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

function MainApp() {
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
          <Route path="/" element={<Cuenta />} />
          <Route path="/retiros" element={<Retiros />} />
          <Route path="/transferencias" element={<Transferencias />} />
          <Route path="/pagos" element={<Pagos />} />
          <Route path="/mas" element={<Mas />} />
          <Route path="*" element={<Cuenta />} />
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

  return (
    <PhoneFrame>
      {onboardingDone ? (
        <MainApp />
      ) : (
        <>
          <Logo />
          <Onboarding onComplete={() => setOnboardingDone(true)} />
        </>
      )}
    </PhoneFrame>
  );
}
