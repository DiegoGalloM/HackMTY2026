import { expect, test, type Page } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { salonHealth } from "./pages/fixtures";
import { AUTH_USER, OnboardingPage, stubProfileStore } from "./pages/OnboardingPage";

/**
 * Cash Insight de punta a punta: la cuenta recién registrada termina la
 * encuesta y Cuenta muestra la lección que disparó su respuesta, en la misma
 * página (sin recargar). Si el negocio ya tiene datos, manda el insight de
 * datos. El backend se simula como en el resto de la suite.
 */

const STOCKOUT_INSIGHT = {
  id: "data_stockout",
  lesson: "inventory",
  title: "Cuándo volver a pedir",
  body: "Estos insumos ya tocaron su punto de reorden: Harina de trigo. Pedir a tiempo evita perder ventas.",
  action: "Calcular mi punto de reorden",
  evidence: { low_stock: ["Harina de trigo"] },
};

// La encuesta de OnboardingPage.fillSurvey: comida y "Sí" a todo, así que se
// cumplen se_ha_quedado_sin_stock y compro_de_mas a la vez.
const SURVEY_TITLE = "No necesitas más inventario; necesitas mejor inventario";

/** API financiera de la cuenta de prueba: overview mínimo e insights a elegir. */
async function stubBusinessApi(page: Page, insights: unknown[]) {
  const calls = { insights: 0 };
  await page.route(new RegExp(`/business/${AUTH_USER.user_id}/`), (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/analytics/insights")) {
      calls.insights += 1;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(insights) });
    }
    if (path.endsWith("/overview")) {
      const overview = { business_name: AUTH_USER.business_name, category: "comida", health: salonHealth("month"), recent_orders: [], recent_purchases: [], pending_review: 0, has_data: false };
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overview) });
    }
    return route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"no simulado"}' });
  });
  return calls;
}

/** Registro → encuesta → "Ir a mi cuenta", marcando la página para detectar una recarga. */
async function finishSurveyAndEnterAccount(page: Page) {
  const onboarding = new OnboardingPage(page);
  await onboarding.goto();
  await stubProfileStore(page);
  await onboarding.fillSurvey({ city: "Austin" });
  await expect(onboarding.successTitle).toBeVisible();
  // Una recarga borraría esta marca: si sigue ahí, la tarjeta llegó sin recargar.
  await page.evaluate(() => {
    (window as unknown as { __sinRecargar: boolean }).__sinRecargar = true;
  });
  await onboarding.accountButton.click();
  const app = new AppPage(page);
  await app.expectOnAccount();
  return app;
}

async function expectNoReload(page: Page) {
  expect(await page.evaluate(() => (window as unknown as { __sinRecargar?: boolean }).__sinRecargar)).toBe(true);
}

test.describe("Cash Insight después de la encuesta", () => {
  test("la respuesta de la encuesta dispara su lección en Cuenta sin recargar", async ({ page }) => {
    const calls = await stubBusinessApi(page, []); // cuenta nueva: sin insights de datos
    const app = await finishSurveyAndEnterAccount(page);

    await expect(app.cashInsight).toContainText(SURVEY_TITLE);
    await expect(app.cashInsight).toHaveAttribute("data-insight-source", "survey");
    await expect(page.locator(".cash-insight-card")).toHaveCount(1);
    await expectNoReload(page);
    expect(calls.insights).toBeGreaterThan(0);

    // La acción abre la micro-lección de inventario.
    await app.cashInsight.getByRole("button", { name: "Separar lo que se vende rápido de lo que no" }).click();
    await expect(page.getByRole("dialog").first()).toBeVisible();
  });

  test("si el negocio ya tiene datos, el insight de datos gana sobre el de la encuesta", async ({ page }) => {
    await stubBusinessApi(page, [STOCKOUT_INSIGHT]);
    const app = await finishSurveyAndEnterAccount(page);

    await expect(app.cashInsight).toContainText("Según tus datos");
    await expect(app.cashInsight).toContainText("Cuándo volver a pedir");
    await expect(app.cashInsight).toHaveAttribute("data-insight-source", "data");
    await expect(page.locator(".cash-insight-card")).toHaveCount(1);
    await expect(page.getByText(SURVEY_TITLE)).toHaveCount(0);
    await expectNoReload(page);
  });

  test("Educación no repite en la lección de la encuesta un tema que ya cubren los datos", async ({ page }) => {
    await stubBusinessApi(page, [STOCKOUT_INSIGHT]);
    await finishSurveyAndEnterAccount(page);

    await page.getByRole("link", { name: /ONE Education/ }).click();
    const titles = page.locator(".cash-insight-card__title");
    await expect(titles.filter({ hasText: "Cuándo volver a pedir" })).toHaveCount(1);
    // La encuesta también dispara "quiebre de stock" (cubierto por los datos),
    // así que su lección pasa a la siguiente que aplica: la sobrecompra.
    await expect(titles.filter({ hasText: "Tu efectivo también se queda atrapado en una caja" })).toHaveCount(1);
    await expect(titles.filter({ hasText: SURVEY_TITLE })).toHaveCount(0);
    await expectNoReload(page);
  });
});
