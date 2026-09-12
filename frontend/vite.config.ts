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
        name: "Monito — Banca Digital",
        short_name: "Monito",
        description: "App de banca digital para HackMTY 2026",
        lang: "es",
        start_url: "./",
        scope: "./",
        display: "standalone",
        orientation: "portrait",
        background_color: "#f5f4f1",
        theme_color: "#2dd4bf",
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
