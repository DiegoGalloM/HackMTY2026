import { expect, test } from "@playwright/test";
import { OnboardingPage, stubAuth } from "./pages/OnboardingPage";

// La app abre en la landing (logo animado + "Empezar"); la bienvenida es la segunda pantalla.
test("la bienvenida aparece tras la landing y ambos accesos llevan a la encuesta", async ({ page }) => {
  // La encuesta ya exige cuenta: lo que se vigila aquí es que llegar a ella no
  // GUARDE el perfil antes de tiempo (el GET tras el login es el que decide
  // si hay que hacer la encuesta; los POST sólo salen al terminarla).
  const guarded: string[] = [];
  page.on("request", request => { if (request.method() === "POST" && request.url().includes("/business-profile/")) guarded.push(request.url()); });
  await stubAuth(page);

  const onboarding = new OnboardingPage(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await expect(page.getByRole("heading", { name: /Tu negocio en tus manos/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /NEGOCIO DEMO/ })).toBeVisible();
  await expect(page.getByText("Selecciona tu modelo de negocio")).toHaveCount(0);

  await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Qué bueno verte de nuevo." })).toBeFocused();
  await onboarding.login();
  // La encuesta empieza pidiendo el nombre; el modelo de negocio viene después.
  await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toBeFocused();
  await onboarding.fillName();
  await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toBeVisible();

  await page.getByRole("button", { name: "Ir al inicio" }).click();
  await onboarding.register();
  await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toBeVisible();
  expect(guarded).toEqual([]);
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
  await onboarding.register();
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

test("tarjeta, registro y encuesta caben en pantallas pequeñas y a 200% de texto", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await stubAuth(page);
  const onboarding = new OnboardingPage(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  const bounds = await page.locator(".reference-card").boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(320);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);

  await expect(page.getByRole("button", { name: "Registrarme", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  // El formulario de registro es lo más ancho de la bienvenida: seis campos,
  // el date picker nativo y el ojo de mostrar contraseña.
  await onboarding.fillRegisterForm();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  const birthdate = await page.getByLabel("Fecha de nacimiento").boundingBox();
  expect(birthdate!.x).toBeGreaterThanOrEqual(0);
  expect(birthdate!.x + birthdate!.width).toBeLessThanOrEqual(320);

  await onboarding.registerSubmit.click();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(overflow).toBe(false);
  await new OnboardingPage(page).fillName();
  await page.addStyleTag({ content: ".survey-step-body h1 { font-size: 50px; }" });
  await expect(page.getByRole("button", { name: "Otro", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Otro", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Actividad de tu negocio" })).toBeVisible();
});

test("la tarjeta sigue al mouse y respeta movimiento reducido", async ({ page, isMobile }) => {
  test.skip(isMobile, "El movimiento solo se activa con mouse.");
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  const card = page.locator(".business-card-surface");
  const bounds = await card.boundingBox();
  await page.mouse.move(bounds!.x + bounds!.width * .85, bounds!.y + bounds!.height * .65);
  await expect.poll(() => card.evaluate(el => getComputedStyle(el).transform)).not.toBe("none");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await page.getByRole("button", { name: "Empezar" }).click();
  const reducedBounds = await card.boundingBox();
  await page.mouse.move(reducedBounds!.x + reducedBounds!.width * .85, reducedBounds!.y + reducedBounds!.height * .65);
  await expect(card).toHaveCSS("transform", "none");
});
