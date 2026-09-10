import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Config pensada para que este mismo build sea servido como web dashboard
// Y empaquetado como app de escritorio con Tauri (ver desktop/README.md) —
// por eso base relativa y puerto fijo (Tauri lo espera en dev).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
  },
});
