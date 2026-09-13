import { expect, test, type Page } from "@playwright/test";
import { AUTH_PASSWORD, AUTH_ROUTE, AUTH_SUCCESS, AUTH_TOKEN, AUTH_USER, LOGIN_ROUTE, OnboardingPage, REGISTER_ROUTE, stubAuth } from "./pages/OnboardingPage";
// Se importa la constante en vez de escribir el número: la política subió de
// 10 a 12 caracteres y este test se quedó atrás afirmando el texto viejo.
import { MIN_PASSWORD_LENGTH } from "../src/auth/passwordPolicy";

const PROFILE_ENDPOINT = "**/business-profile/**";

/** Deja la app en la bienvenida, que es donde viven registro y login. */
async function openWelcome(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Empezar" }).click();
  await expect(page.getByRole("heading", { name: /Tu negocio.*en tus manos/i })).toBeVisible();
}

/** Cuenta cuántas veces se llamó de verdad a /auth/* y responde el status dado. */
async function countAuthCalls(page: Page, status: number, body: unknown) {
  const urls: string[] = [];
  await page.route(AUTH_ROUTE, (route) => {
    urls.push(route.request().url());
    return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
  return urls;
}

test.describe("Registro e inicio de sesión", () => {
  test("un registro exitoso guarda la sesión y lleva a la encuesta", async ({ page }) => {
    const bodies: any[] = [];
    // stubAuth responde el GET del perfil (null: cuenta nueva); el handler del
    // registro va después para tener prioridad y capturar el cuerpo.
    await stubAuth(page);
    await page.route(REGISTER_ROUTE, (route) => {
      bodies.push(route.request().postDataJSON());
      return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(AUTH_SUCCESS) });
    });

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await onboarding.register();

    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toBeVisible();

    // El contrato de POST /auth/register: estos son los campos que valida el
    // backend. El usuario viaja en minúsculas y sin espacios.
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).toEqual({
      username: AUTH_USER.username,
      business_name: AUTH_USER.business_name,
      full_name: AUTH_USER.full_name,
      birthdate: AUTH_USER.birthdate,
      password: AUTH_PASSWORD,
    });

    // La sesión queda en sessionStorage para que el POST de la encuesta la use.
    const stored = await page.evaluate(() => sessionStorage.getItem("c1b.session"));
    expect(stored).toContain(AUTH_TOKEN);
    expect(stored).not.toContain(AUTH_PASSWORD);
  });

  test("un usuario repetido (409) se explica en español y no borra lo capturado", async ({ page }) => {
    await page.route(REGISTER_ROUTE, (route) =>
      route.fulfill({ status: 409, contentType: "application/json", body: '{"detail":"username_taken"}' }),
    );

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await onboarding.register();

    await expect(page.getByRole("alert")).toContainText(/usuario ya está registrado/i);
    // Sigue en el formulario, con todo lo que escribió intacto.
    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toHaveCount(0);
    await expect(page.getByLabel("Nombre de tu negocio")).toHaveValue(AUTH_USER.business_name);
    await expect(page.getByLabel("Contraseña", { exact: true })).toHaveValue(AUTH_PASSWORD);
    await expect(onboarding.registerSubmit).toBeEnabled();
  });

  test("una contraseña débil se bloquea en el cliente, sin pegarle al backend", async ({ page }) => {
    const calls = await countAuthCalls(page, 201, AUTH_SUCCESS);

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await onboarding.register({ password: "corto" });

    await expect(page.getByRole("alert").first()).toBeVisible();
    await expect(
      page.getByText(new RegExp(`al menos ${MIN_PASSWORD_LENGTH} caracteres`, "i")).first(),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toHaveCount(0);
    // Lo importante: la política del servidor se espeja en el cliente, así que
    // una contraseña que el backend rechazaría nunca sale del navegador.
    expect(calls).toEqual([]);
  });

  test("credenciales inválidas (401) muestran el mensaje en español", async ({ page }) => {
    await page.route(LOGIN_ROUTE, (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"invalid_credentials"}' }),
    );

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await onboarding.login({ password: "otraCosa123" });

    await expect(page.getByRole("alert")).toContainText(/Usuario o contraseña incorrectos/i);
    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toHaveCount(0);
    await expect(page.getByLabel("Usuario", { exact: true })).toHaveValue(AUTH_USER.username);
  });

  test("si el backend no responde, el registro explica que no hay conexión", async ({ page }) => {
    await page.route(AUTH_ROUTE, (route) => route.abort("connectionrefused"));

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await onboarding.register();

    await expect(page.getByRole("alert")).toContainText(/No se pudo conectar con el servidor/i);
    await expect(onboarding.registerSubmit).toBeEnabled();
  });

  test("un login exitoso lleva a la encuesta", async ({ page }) => {
    await stubAuth(page);

    const onboarding = new OnboardingPage(page);
    await openWelcome(page);
    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await onboarding.login();

    await expect(page.getByRole("heading", { name: "¿Cómo te llamas?" })).toBeVisible();
  });

  test("el POST de la encuesta viaja con el token de la respuesta de auth", async ({ page }) => {
    let authorization: string | undefined;
    let url = "";
    await page.route(PROFILE_ENDPOINT, async (route) => {
      authorization = route.request().headers()["authorization"];
      url = route.request().url();
      await route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' });
    });

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey();

    await expect(onboarding.successTitle).toBeVisible();
    expect(authorization).toBe(`Bearer ${AUTH_TOKEN}`);
    // El owner_id de la URL es el user_id real de la cuenta, no "demo-owner".
    expect(url).toContain(`/business-profile/${AUTH_USER.user_id}`);
  });

  test("un 401 en el perfil avisa que la sesión expiró, no un error genérico", async ({ page }) => {
    await page.route(PROFILE_ENDPOINT, (route) =>
      route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"Not authenticated"}' }),
    );

    const onboarding = new OnboardingPage(page);
    await onboarding.completeSurvey();

    await expect(onboarding.failureTitle).toBeVisible();
    await expect(onboarding.errorMessage).toContainText(/sesión expiró/i);
    await expect(onboarding.successTitle).toHaveCount(0);
  });

  test("Explorar la demo llega a la cuenta sin registrarse", async ({ page }) => {
    const calls: string[] = [];
    page.on("request", (request) => {
      // AUTH_ROUTE y no "/auth/": los modulos del front viven en /src/auth/.
      if (AUTH_ROUTE.test(request.url()) || request.url().includes("/business-profile/")) calls.push(request.url());
    });

    await openWelcome(page);
    await page.getByRole("button", { name: "Explorar la demo" }).click();
    // Un toque más: elegir el negocio de ejemplo.
    await expect(page.getByRole("dialog", { name: "Elige un negocio de ejemplo" })).toBeVisible();
    await page.getByRole("button", { name: /Panadería La Espiga/ }).click();

    await expect(page.locator(".reference-card img")).toHaveAttribute("src", /capital-one-main-page-card/);
    await expect(page.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
    // La demo abierta no toca ningún endpoint protegido.
    expect(calls).toEqual([]);
  });
});
