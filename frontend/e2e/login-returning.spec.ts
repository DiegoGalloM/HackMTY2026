import { expect, test } from "@playwright/test";
import { AppPage } from "./pages/AppPage";
import { AUTH_USER, OnboardingPage, stubProfileStore } from "./pages/OnboardingPage";

/**
 * Una cuenta que ya hizo la encuesta entra directo a Cuenta; una que todavía
 * no la termina vuelve a verla. La regla es una sola: después de cualquier
 * autenticación se lee el perfil y él decide.
 */
test.describe("Login de una cuenta existente", () => {
  test("registro → encuesta → cuenta → cerrar sesión → login entra directo a Cuenta", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    const app = new AppPage(page);
    // goto() registra stubAuth (GET del perfil → null); el store con memoria
    // se registra después para que el GET regrese lo que guardó el POST.
    await onboarding.goto();
    const store = await stubProfileStore(page);
    await onboarding.fillSurvey({ city: "Monterrey" });
    await expect(onboarding.successTitle).toBeVisible();
    expect(store.posts).toHaveLength(1);
    await onboarding.accountButton.click();
    await app.expectOnAccount();
    await expect(app.greeting("Carlos")).toBeVisible();

    await app.logout();
    // Sin sesión ni perfil local en el dispositivo.
    expect(await page.evaluate(() => sessionStorage.getItem("c1b.session"))).toBeNull();
    expect(await page.evaluate(() => sessionStorage.getItem("c1b.profile"))).toBeNull();

    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await onboarding.login();

    // Directo a Cuenta: saludo con el nombre de la cuenta y la lección de la
    // categoría/respuestas guardadas (comida + todo "Sí"). Nunca la encuesta.
    await app.expectOnAccount();
    await expect(app.greeting(AUTH_USER.full_name.split(" ")[0])).toBeVisible();
    await expect(app.cashInsight).toBeVisible();
    await expect(app.cashInsight).toContainText(/inventario/i);
    await app.expectNotInSurvey();
    expect(store.posts).toHaveLength(1); // el login no vuelve a guardar nada
  });

  test("registro sin terminar la encuesta → volver a entrar → encuesta otra vez", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await stubProfileStore(page); // nada guardado todavía
    // Se cierra la pestaña a media encuesta: al volver, sin sesión ni perfil.
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await page.getByRole("button", { name: "Empezar" }).click();
    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await onboarding.login();

    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Navegación principal" })).toHaveCount(0);
  });

  test("mientras se lee el perfil el botón sigue ocupado y no se ve la encuesta", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await page.route(/\/business-profile\/[^/?]+$/, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 600));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ category: "belleza", category_detail: null, operating_days: ["tue"], city: "Monterrey", employees: "2", answers: { usa_insumos_belleza: true }, week_description_mode: "text", week_description_text: "" }) });
    });
    await page.evaluate(() => sessionStorage.clear());
    await page.reload();
    await page.getByRole("button", { name: "Empezar" }).click();
    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await onboarding.login();

    await expect(page.getByRole("button", { name: /Entrando…/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toHaveCount(0);
    const app = new AppPage(page);
    await app.expectOnAccount();
    await expect(app.cashInsight).toContainText(/cita/i); // lección de belleza
  });
});
