import { defineConfig, devices } from "@playwright/test";

// Los tests corren contra el dev server de Vite, que Playwright levanta solo.
// El backend NO hace falta: cada test intercepta POST /business-profile con
// page.route(), asi son deterministas y no escriben en Snowflake real.
//
// E2E_PORT permite correr la suite con otro puerto cuando el 5173 ya lo tiene
// otro dev server (p. ej. otra copia del repo): E2E_PORT=5175 npm run e2e.
const PORT = Number(process.env.E2E_PORT ?? 5173);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html"], ["junit", { outputFile: "playwright-report/junit.xml" }]] : "list",

  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    // La app es una PWA pensada para celular: este proyecto cubre ese caso.
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],

  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
