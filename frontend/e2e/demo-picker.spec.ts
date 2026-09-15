import { expect, test } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { SALON_SESSION, SALON_USER, salonHealth, salonOverview } from "./pages/fixtures";

/**
 * "Explorar la demo" ofrece dos negocios; el salón entra con su nombre, el
 * Cash Insight de sus datos (que gana sobre la lección de belleza de la
 * encuesta) y un resumen de apertura con sus datos. El backend se
 * simula con las respuestas mínimas que leen Cuenta y Análisis.
 */
test("Explorar la demo → estética → Cuenta con Cash Insight y Análisis con resumen de apertura", async ({ page }) => {
  const sessions: unknown[] = [];
  await page.route(/\/demo\/session$/, (route) => {
    sessions.push(route.request().postDataJSON());
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SALON_SESSION) });
  });
  await page.route(new RegExp(`/business/${SALON_USER.user_id}/overview$`), (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(salonOverview()) }),
  );
  // El salón sembrado tiene inventario atorado: /analytics/insights lo reporta.
  await page.route(new RegExp(`/business/${SALON_USER.user_id}/analytics/insights$`), (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([{ id: "data_overstock", lesson: "inventory", title: "Tu efectivo también se queda atrapado en el almacén", body: "Tu inventario tarda en venderse.", action: "Ver qué se está moviendo lento", evidence: {} }]),
    }),
  );
  await page.route(new RegExp(`/business/${SALON_USER.user_id}/analytics/health`), (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(salonHealth("week")) }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await page.getByRole("button", { name: "Explorar la demo" }).click();

  const sheet = page.getByRole("dialog", { name: "Elige un negocio de ejemplo" });
  await expect(sheet).toBeVisible();
  await expect(sheet.getByRole("button", { name: /Panadería La Espiga/ })).toContainText("Austin, TX · comida");
  await expect(sheet.getByRole("button", { name: /Estética Carolina/ })).toContainText("Monterrey, MX · belleza");
  await sheet.getByRole("button", { name: /Estética Carolina/ }).click();

  expect(sessions).toEqual([{ business: "estetica" }]);
  const app = new AppPage(page);
  await app.expectOnAccount();
  await expect(page.getByText("Efectivo de Estética Carolina")).toBeVisible();
  await expect(app.greeting("Carolina")).toBeVisible();
  // Con datos, Cuenta muestra el insight de datos y no la lección de la encuesta.
  await expect(app.cashInsight).toContainText("Según tus datos");
  await expect(app.cashInsight).toContainText("Tu efectivo también se queda atrapado en el almacén");
  await expect(page.getByText("¿Cuánto te deja realmente una cita?")).toHaveCount(0);

  // El botón central abre el chat con el resumen de apertura del salón.
  await app.openTab("Análisis");
  const brief = page.getByTestId("opening-brief");
  await expect(brief).toBeVisible();
  await expect(brief).toContainText("Tu efectivo cubre lo que debes pronto");
  await expect(brief).toContainText("$12,480.00");
  await expect(brief).toContainText("Insumos por agotarse");
  await expect(brief).toContainText("Tinte (tubo)");
  // Cada punto de atención es un chip con su pregunta.
  await expect(page.getByRole("button", { name: "¿Qué insumo se me va a acabar primero?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "¿Por qué bajó mi utilidad este mes?" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver resumen" })).toBeVisible();
});
