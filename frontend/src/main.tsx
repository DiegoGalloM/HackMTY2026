import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { initErrorTracking } from "./observability";
import "./index.css";
import "./theme.css";

// HashRouter y no BrowserRouter: el build usa `base: "./"` porque el mismo
// bundle se sirve como web app Y se empaqueta como app de escritorio
// (ver desktop/README.md). Con hash, recargar en /pagos no da 404 ni hace
// falta rewrite en el servidor.
// Sin VITE_SENTRY_DSN no hace nada (ni descarga el SDK). No se espera: la app
// no debe tardar en arrancar por el tracking de errores.
void initErrorTracking();

const container = document.getElementById("root");
if (!container) throw new Error("No se encontró #root en index.html");

createRoot(container).render(
  <StrictMode>
    <HashRouter>
      {/* Último recurso: si truena algo fuera de las pantallas (landing,
          bienvenida, encuesta), se muestra un mensaje y no una página en blanco. */}
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </HashRouter>
  </StrictMode>,
);
