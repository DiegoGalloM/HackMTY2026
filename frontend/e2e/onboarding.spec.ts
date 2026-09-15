import { expect, test } from "@playwright/test";
import { OnboardingPage } from "./pages/OnboardingPage";

const PROFILE_ENDPOINT = "**/business-profile/**";

test.describe("Encuesta de onboarding", () => {
  test("guarda el perfil y manda al backend el payload que espera BusinessProfile", async ({ page }) => {
    let body: any = null;

    await page.route(PROFILE_ENDPOINT, async (route) => {
      body = route.request().postDataJSON();
      await route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' });
    });

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey({ city: "Monterrey" });

    await expect(onboarding.successTitle).toBeVisible();
    await expect(onboarding.accountButton).toBeVisible();
    await expect(onboarding.retryButton).toHaveCount(0);

    // El contrato con el backend: estos son los campos que snowflake_store
    // escribe en business_profiles. Si el front deja de mandar alguno, el dato
    // se pierde en silencio — igual que pasó con el audio.
    expect(body).toMatchObject({
      category: "comida",
      city: "Monterrey",
      employees: "1",
      week_description_mode: "text",
    });
    expect(body.operating_days).toEqual(["mon", "tue"]);
    expect(body.week_description_text).toContain("mercancía");
    expect(Object.values(body.answers).length).toBeGreaterThan(0);
  });

  test("un 500 del backend NO se reporta como guardado exitoso", async ({ page }) => {
    await page.route(PROFILE_ENDPOINT, (route) =>
      route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' }),
    );

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey();

    await expect(onboarding.failureTitle).toBeVisible();
    await expect(onboarding.errorMessage).toContainText("500");
    await expect(onboarding.retryButton).toBeVisible();
    // Lo importante: nunca dice que quedó guardado.
    await expect(onboarding.successTitle).toHaveCount(0);
    await expect(page.getByText("Tu perfil de negocio quedó guardado.")).toHaveCount(0);
  });

  test("un 413 (grabación demasiado grande) explica qué hacer en vez de mostrar el código", async ({ page }) => {
    await page.route(PROFILE_ENDPOINT, (route) =>
      route.fulfill({ status: 413, contentType: "application/json", body: '{"detail":"payload_too_large"}' }),
    );

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey();

    await expect(onboarding.failureTitle).toBeVisible();
    await expect(onboarding.errorMessage).toContainText("Graba una más corta o escribe cómo es tu semana");
    await expect(onboarding.errorMessage).not.toContainText("413");
  });

  test("si el backend no responde, explica que no hay conexión", async ({ page }) => {
    await page.route(PROFILE_ENDPOINT, (route) => route.abort("connectionrefused"));

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey();

    await expect(onboarding.failureTitle).toBeVisible();
    await expect(onboarding.errorMessage).toContainText(/No se pudo conectar/);
  });

  test("Reintentar vuelve a mandar las mismas respuestas sin recapturarlas", async ({ page }) => {
    let attempts = 0;
    const payloads: any[] = [];

    await page.route(PROFILE_ENDPOINT, async (route) => {
      attempts += 1;
      payloads.push(route.request().postDataJSON());
      if (attempts === 1) {
        await route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
      } else {
        await route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' });
      }
    });

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey({ city: "Guadalajara" });

    await expect(onboarding.failureTitle).toBeVisible();
    await onboarding.retryButton.click();

    await expect(onboarding.successTitle).toBeVisible();
    expect(attempts).toBe(2);
    // El segundo intento manda exactamente lo mismo: no se perdió nada.
    expect(payloads[1]).toEqual(payloads[0]);
    expect(payloads[1].city).toBe("Guadalajara");
  });

  test("avisa para qué se usan las respuestas y cuánto dura la grabación", async ({ page }) => {
    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await onboarding.pickCategory("Comida y bebidas");

    // Consentimiento del benchmarking entre negocios, en cada pregunta.
    await expect(page.getByText(/de forma agregada y anónima, ayudan a comparar tu categoría de negocio/)).toBeVisible();
    await expect(page.getByText(/5 o más negocios, nunca respuestas de uno solo/)).toBeVisible();

    await onboarding.answerAllQuestions("Sí");
    await page.getByRole("button", { name: "Narrar" }).click();
    // Espejo de ONBOARDING_AUDIO_RETENTION_DAYS: el audio caduca.
    await expect(page.getByText(/se borra automáticamente a los 7 días/)).toBeVisible();
  });

  test("la ubicación sólo va a OpenStreetMap si la persona la pide, y se avisa antes", async ({ page, context }) => {
    const lookups: string[] = [];
    await page.route("https://nominatim.openstreetmap.org/**", async (route) => {
      lookups.push(route.request().url());
      await route.fulfill({ status: 200, contentType: "application/json", body: '{"address":{"city":"Monterrey"}}' });
    });
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation({ latitude: 25.67, longitude: -100.31 });

    const onboarding = new OnboardingPage(page);
    await onboarding.goto();
    await onboarding.reachCityStep();

    await expect(page.getByText(/envía tus coordenadas a OpenStreetMap \(Nominatim\)/)).toBeVisible();
    expect(lookups).toHaveLength(0);

    await page.getByRole("button", { name: "Usar mi ubicación" }).click();
    await expect(onboarding.cityInput).toHaveValue("Monterrey");
    expect(lookups).toHaveLength(1);
    expect(lookups[0]).toContain("lat=25.67");
  });
});
