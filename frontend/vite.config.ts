import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

// Base relativa + puerto fijo: este mismo build se sirve como web app Y se
// empaqueta como app de escritorio con Tauri (ver desktop/README.md).
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "Capital One Business — Flujo de efectivo para microempresas",
        // short_name es lo que cabe debajo del icono en la pantalla de inicio:
        // arriba de ~12 caracteres el sistema lo trunca con puntos suspensivos.
        short_name: "C1 Business",
        description:
          "Gestión de flujo de efectivo para microempresas: construye liquidez y aprende finanzas sobre la marcha.",
        lang: "es",
        start_url: "./",
        scope: "./",
        display: "standalone",
        orientation: "portrait",
        background_color: "#f4f6f9",
        theme_color: "#13294b",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "pwa-maskable-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        // The supplied main-page card is 2.58 MB; keep it available offline.
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
      },
      devOptions: {
        // Permite probar el service worker con `npm run dev`.
        enabled: true,
        type: "module",
      },
    }),
  ],
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
  },
});
