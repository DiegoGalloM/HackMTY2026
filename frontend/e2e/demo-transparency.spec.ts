import { expect, test, type Page } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { SALON_SESSION } from "./pages/fixtures";

/**
 * Transparencia (fases 1 y 8 del roadmap): quien ve UNA sola de estas
 * pantallas ya entiende que es una demo con dinero simulado y que no es un
 * producto de Capital One. Cada test mira una superficie por separado.
 */

const DEMO_TEXT = /todas las transacciones son simuladas/i;
const NO_REAL_MONEY = /No se procesa dinero real ni se conecta a cuentas bancarias reales/;
const NOT_AFFILIATED = /No es un producto de Capital One ni está afiliado, respaldado o patrocinado por Capital One, N\.A\./;
const BADGE = "Modo demo — datos simulados";

async function expectFullNotice(page: Page) {
  const notice = page.getByRole("complementary", { name: "Aviso de demo" });
  await notice.scrollIntoViewIfNeeded();
  await expect(notice).toBeVisible();
  await expect(notice).toContainText(DEMO_TEXT);
  await expect(notice).toContainText(NO_REAL_MONEY);
  await expect(notice).toContainText(NOT_AFFILIATED);
}

test("la landing avisa que es una demo con dinero simulado desde el primer instante", async ({ page }) => {
  await page.goto("/");
  // Sin esperar la intro animada del logo (3 s): el aviso no forma parte de ella.
  await expectFullNotice(page);
  await expect(page.getByRole("button", { name: "Empezar" })).toBeVisible();
});

test("en un celular chico el aviso de la landing se alcanza y no desborda", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/");
  await expectFullNotice(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  const button = page.getByRole("button", { name: "Empezar" });
  await button.scrollIntoViewIfNeeded();
  await button.click();
  await expect(page.getByRole("heading", { name: /Tu negocio en tus manos/ })).toBeVisible();
});

test.describe("página pública de pago", () => {
  const TOKEN = "tok_transparencia_0123456789abcdef";

  test("una orden por pagar muestra el aviso de demo y de no afiliación", async ({ page }) => {
    await page.route(new RegExp(`/pay/${TOKEN}$`), (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          business_name: "Panadería La Espiga",
          order_number: 42,
          status: "AWAITING_PAYMENT",
          currency: "USD",
          lines: [{ item_name: "Concha", quantity: 2, unit_price: 1.75, line_total: 3.79 }],
          subtotal: 3.5,
          tax_total: 0.29,
          total: 3.79,
          paid_at: null,
          payment: null,
          provider: { provider: "demo", mode: "test" },
        }),
      }),
    );
    await page.goto(`/#/pay/${TOKEN}`);
    await expect(page.getByRole("button", { name: /Pagar/ })).toBeVisible();
    await expect(page.getByText("Pago de prueba")).toBeVisible();
    await expectFullNotice(page);
  });

  test("un código que no existe también lleva el aviso", async ({ page }) => {
    await page.route(new RegExp(`/pay/${TOKEN}$`), (route) =>
      route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"order_not_found"}' }),
    );
    await page.goto(`/#/pay/${TOKEN}`);
    await expect(page.getByRole("heading", { name: "No encontramos esta orden" })).toBeVisible();
    await expectFullNotice(page);
  });
});

test("dentro de la app la franja de demo acompaña cada pantalla sin tapar el contenido", async ({ page }) => {
  await page.route(/\/demo\/session$/, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(SALON_SESSION) }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await page.getByRole("button", { name: "Explorar la demo" }).click();
  await page.getByRole("dialog", { name: "Elige un negocio de ejemplo" }).getByRole("button", { name: /Estética Carolina/ }).click();

  const app = new AppPage(page);
  await app.expectOnAccount();
  const badge = app.nav.getByRole("note");

  for (const tab of ["Cuenta", "Compras", "Más"] as const) {
    await app.openTab(tab);
    await expect(badge).toHaveText(BADGE);
    await expect(badge).toBeInViewport();
    // El padding inferior de la pantalla reserva al menos el alto de toda la
    // barra (íconos + franja): el final del contenido nunca queda debajo.
    // Se mide con poll: durante la transición conviven la pantalla que sale y
    // la que entra, y la que sale ya no tiene estilos calculados.
    const navHeight = (await app.nav.boundingBox())!.height;
    await expect
      .poll(() => page.locator("main").last().evaluate((el) => parseFloat(getComputedStyle(el).paddingBottom) || 0))
      .toBeGreaterThanOrEqual(navHeight);
  }
});

test("el registro recuerda que el dinero es simulado", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  await expect(page.getByText("Estás en la versión de demostración.")).toBeVisible();
  await expect(page.getByText(/Todas las transacciones son simuladas: no se procesa dinero real/)).toBeVisible();
});
