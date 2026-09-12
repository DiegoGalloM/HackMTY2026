import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import BottomNav from "./components/BottomNav";
import Cuenta from "./screens/Cuenta";
import Mas from "./screens/Mas";
import Pagos from "./screens/Pagos";
import Retiros from "./screens/Retiros";
import Transferencias from "./screens/Transferencias";

export default function App() {
  const location = useLocation();

  return (
    // El shell ocupa 100dvh y no scrollea; el scroll vive dentro de cada
    // pantalla (ver Screen.tsx), así la barra inferior nunca se mueve.
    <div className="relative mx-auto flex h-full max-w-md flex-col overflow-hidden bg-surface">
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
