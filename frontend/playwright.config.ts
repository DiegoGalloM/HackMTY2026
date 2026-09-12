import { defineConfig, devices } from "@playwright/test";

// Los tests corren contra el dev server de Vite, que Playwright levanta solo.
// El backend NO hace falta: cada test intercepta POST /business-profile con
// page.route(), asi son deterministas y no escriben en Snowflake real.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html"], ["junit", { outputFile: "playwright-report/junit.xml" }]] : "list",

  use: {
    baseURL: "http://localhost:5173",
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
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
