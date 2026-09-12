import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

// HashRouter y no BrowserRouter: el build usa `base: "./"` porque el mismo
// bundle se sirve como web app Y se empaqueta como app de escritorio
// (ver desktop/README.md). Con hash, recargar en /pagos no da 404 ni hace
// falta rewrite en el servidor.
const container = document.getElementById("root");
if (!container) throw new Error("No se encontró #root en index.html");

createRoot(container).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
