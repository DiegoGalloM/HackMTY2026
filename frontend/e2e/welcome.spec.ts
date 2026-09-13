import { expect, test } from "@playwright/test";
import { OnboardingPage } from "./pages/OnboardingPage";

test("la bienvenida aparece primero y ambos accesos demo llevan a la encuesta", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", request => { if (request.method() === "POST") requests.push(request.url()); });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Tu negocio. Tu esfuerzo./ })).toBeVisible();
  await expect(page.getByRole("img", { name: /NEGOCIO DEMO/ })).toBeVisible();
  await expect(page.getByText("Selecciona tu modelo de negocio")).toHaveCount(0);
  await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Qué bueno verte de nuevo." })).toBeFocused();
  await expect(page.getByText(/No se crea una cuenta real/)).toBeVisible();
  await page.getByRole("button", { name: "Continuar a mi encuesta" }).click();
  await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toBeFocused();
  await page.getByRole("button", { name: "Ir al inicio" }).click();
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  await page.getByRole("button", { name: "Comenzar mi encuesta" }).click();
  await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toBeVisible();
  expect(requests).toEqual([]);
});

test("volver a la pregunta anterior o al inicio conserva las respuestas", async ({ page }) => {
  const onboarding = new OnboardingPage(page);
  await onboarding.goto();
  await onboarding.pickCategory("Comida y bebidas");
  const firstQuestion = await page.locator("#survey-title").textContent();
  await page.getByRole("button", { name: "Sí", exact: true }).click();
  await page.getByRole("button", { name: "Volver a la pregunta anterior" }).click();
  await expect(page.locator("#survey-title")).toHaveText(firstQuestion!);
  await expect(page.getByRole("button", { name: "Sí", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Ir al inicio" }).click();
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  await page.getByRole("button", { name: "Comenzar mi encuesta" }).click();
  await expect(page.getByRole("button", { name: "Sí", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#survey-title")).toBeFocused();
});

test("el recorrido completo vuelve a Cuenta con la imagen original", async ({ page }) => {
  await page.route("**/business-profile/**", route => route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' }));
  const onboarding = new OnboardingPage(page);
  await onboarding.completeSurvey();
  await onboarding.accountButton.click();
  await expect(page.locator(".reference-card img")).toHaveAttribute("src", /capital-one-main-page-card/);
  await expect(page.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Accesos rápidos" })).toHaveClass(/\bgrid\b/);
});

test("tarjeta y encuesta caben en pantallas pequeñas y a 200% de texto", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto("/");
  const bounds = await page.locator(".reference-card").boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await expect(page.getByRole("button", { name: "Registrarme", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  await page.getByRole("button", { name: "Comenzar mi encuesta" }).click();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(overflow).toBe(false);
  await page.addStyleTag({ content: ".survey-step-body h1 { font-size: 50px; }" });
  await expect(page.getByRole("button", { name: "Otro", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Otro", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Actividad de tu negocio" })).toBeVisible();
});

test("la tarjeta sigue al mouse y respeta movimiento reducido", async ({ page, isMobile }) => {
  test.skip(isMobile, "El movimiento solo se activa con mouse.");
  await page.goto("/");
  const card = page.locator(".business-card-surface");
  const bounds = await card.boundingBox();
  await page.mouse.move(bounds!.x + bounds!.width * .85, bounds!.y + bounds!.height * .65);
  await expect.poll(() => card.evaluate(el => getComputedStyle(el).transform)).not.toBe("none");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  const reducedBounds = await card.boundingBox();
  await page.mouse.move(reducedBounds!.x + reducedBounds!.width * .85, reducedBounds!.y + reducedBounds!.height * .65);
  await expect(card).toHaveCSS("transform", "none");
});
