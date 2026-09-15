import { expect, test } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { SALON_SESSION, SALON_USER, salonOverview } from "./pages/fixtures";

/**
 * Fase 6: visibilidad de errores en el frontend. Sin VITE_SENTRY_DSN (como en
 * CI) el SDK no se descarga, pero una pantalla que truena igual muestra un
 * mensaje con salida en vez de dejar la app en blanco.
 */

test("si una pantalla truena, se ve un mensaje con salida y la app sigue navegable", async ({ page }) => {
  // Contrato roto del API: recent_orders llega null y Cuenta no lo soporta.
  await page.route(/\/demo\/session$/, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SALON_SESSION) }),
  );
  await page.route(new RegExp(`/business/${SALON_USER.user_id}/overview$`), (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...salonOverview(), recent_orders: null }) }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await page.getByRole("button", { name: "Explorar la demo" }).click();
  await page.getByRole("dialog", { name: "Elige un negocio de ejemplo" }).getByRole("button", { name: /Estética Carolina/ }).click();

  const app = new AppPage(page);
  const fallback = page.getByRole("alert").filter({ hasText: "Algo salió mal en esta pantalla" });
  await expect(fallback).toBeVisible();
  await expect(fallback.getByRole("button", { name: "Ir a Cuenta" })).toBeVisible();
  // La barra inferior queda fuera del error: se puede seguir a otra pantalla.
  await expect(app.nav).toBeVisible();
  await app.openTab("Más");
  await expect(fallback).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
});

test("sin DSN el SDK de Sentry ni siquiera se descarga", async ({ page }) => {
  const sentryRequests: string[] = [];
  page.on("request", (request) => {
    if (/sentry/i.test(request.url())) sentryRequests.push(request.url());
  });
  await page.route(/\/demo\/session$/, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SALON_SESSION) }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await page.getByRole("button", { name: "Explorar la demo" }).click();
  await page.getByRole("dialog", { name: "Elige un negocio de ejemplo" }).getByRole("button", { name: /Estética Carolina/ }).click();
  await new AppPage(page).expectOnAccount();

  expect(sentryRequests).toEqual([]);
});

test("lo que se mandaría a Sentry sale sin token del QR ni query strings", async ({ page }) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    const mod = await import("/src/observability.ts");
    const event = mod.scrubEvent({
      type: undefined,
      request: { url: "https://demo.example.com/#/pay/tok_secreto_123", headers: { Authorization: "Bearer x" }, query_string: "key=abc" },
      user: { ip_address: "1.2.3.4" },
      exception: { values: [{ type: "TypeError", value: "fallo en http://api.example.com/x?key=abc" }] },
      breadcrumbs: [
        { category: "navigation", data: { from: "/#/", to: "/#/pay/tok_secreto_123" } },
        { category: "fetch", data: { url: "http://localhost:8000/pay/tok_secreto_123?key=abc" } },
      ],
    } as never);
    return JSON.stringify(event);
  });
  for (const leak of ["tok_secreto_123", "key=abc", "Bearer x", "1.2.3.4"]) {
    expect(result).not.toContain(leak);
  }
  expect(result).toContain("/pay/[token]");
});
