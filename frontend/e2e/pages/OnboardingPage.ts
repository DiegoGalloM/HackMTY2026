import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Datos de la cuenta de prueba. Viven aqui (y no en cada spec) para que el
 * token que stubeamos en /auth sea el mismo que después verificamos en el
 * header Authorization del POST de la encuesta.
 */
export const AUTH_TOKEN = "e2e-token-abc123";
export const AUTH_PASSWORD = "TacosDelBarrio26";
export const AUTH_USER = {
  user_id: "usr_e2e_0001",
  username: "donbeto",
  business_name: "Tacos Don Beto",
  full_name: "Beto Ramirez",
  birthdate: "1990-05-04",
};
export const AUTH_SUCCESS = {
  access_token: AUTH_TOKEN,
  token_type: "bearer",
  expires_in: 3600,
  user: AUTH_USER,
};

// Endpoints de auth del backend.
//
// Van como RegExp y NO como glob de comodines sobre /auth/: el propio codigo de
// la app se sirve desde /src/auth/ en el dev server, asi que un glob amplio
// interceptaba los modulos del front y la pantalla se quedaba en blanco.
export const AUTH_ROUTE = /\/auth\/(register|login|me)\b/;
export const REGISTER_ROUTE = /\/auth\/register\b/;
export const LOGIN_ROUTE = /\/auth\/login\b/;
/** GET /business-profile/{owner_id}: el perfil guardado (o null). */
export const PROFILE_ROUTE = /\/business-profile\/[^/?]+$/;

/**
 * Intercepta /auth/* para que la suite siga siendo hermetica: no hace falta
 * backend ni base de datos para recorrer el registro o el login.
 *
 * También responde el GET del perfil que la app hace después de cualquier
 * login o registro: con `profile` null (el default) la cuenta es nueva y la
 * app manda a la encuesta. Los POST del perfil se dejan pasar (fallback) a
 * los handlers que cada test registre.
 */
export async function stubAuth(page: Page, body: unknown = AUTH_SUCCESS, { profile = null }: { profile?: unknown } = {}) {
  await page.route(AUTH_ROUTE, (route) =>
    route.fulfill({
      // El contrato: 201 al registrar, 200 al iniciar sesión.
      status: route.request().url().includes("/auth/register") ? 201 : 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  );
  await page.route(PROFILE_ROUTE, (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(profile) });
  });
}

/**
 * Perfil con memoria: el POST de la encuesta lo guarda y el GET lo regresa,
 * como hace el backend. Registrar DESPUÉS de stubAuth: en Playwright el último
 * handler registrado es el que atiende primero.
 */
export async function stubProfileStore(page: Page) {
  const store: { saved: unknown | null; posts: unknown[] } = { saved: null, posts: [] };
  await page.route(PROFILE_ROUTE, (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      store.saved = request.postDataJSON();
      store.posts.push(store.saved);
      return route.fulfill({ status: 200, contentType: "application/json", body: '{"status":"ok"}' });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(store.saved) });
  });
  return store;
}

/**
 * Page Object de la encuesta de onboarding.
 *
 * Los selectores van por texto visible / rol, no por clase CSS: las clases
 * (`ob-continue`, `bubble`) cambian cuando se retoca el diseño y romperian los
 * tests sin que nada este realmente mal.
 */
export class OnboardingPage {
  readonly page: Page;
  readonly continueButton: Locator;
  readonly cityInput: Locator;
  readonly weekTextarea: Locator;

  constructor(page: Page) {
    this.page = page;
    this.continueButton = page.getByRole("button", { name: "Continuar" });
    this.cityInput = page.getByPlaceholder("O escribe tu ciudad");
    this.weekTextarea = page.getByPlaceholder(/Los lunes recibo mercancía/);
  }

  // --- registro / login -----------------------------------------------------
  async fillRegisterForm(overrides: Partial<typeof AUTH_USER & { password: string }> = {}) {
    const data = { ...AUTH_USER, password: AUTH_PASSWORD, ...overrides };
    await this.page.getByLabel("Nombre de tu negocio").fill(data.business_name);
    await this.page.getByLabel("Tu nombre completo").fill(data.full_name);
    await this.page.getByLabel("Fecha de nacimiento").fill(data.birthdate);
    await this.page.getByLabel("Usuario", { exact: true }).fill(data.username);
    await this.page.getByLabel("Contraseña", { exact: true }).fill(data.password);
    await this.page.getByLabel("Confirmar contraseña").fill(data.password);
  }

  get registerSubmit() {
    return this.page.getByRole("button", { name: "Crear mi cuenta" });
  }
  get loginSubmit() {
    return this.page.getByRole("button", { name: "Entrar a mi cuenta" });
  }

  /** Abre el formulario de registro desde la bienvenida y lo manda. */
  async register(overrides?: Partial<typeof AUTH_USER & { password: string }>) {
    await this.page.getByRole("button", { name: "Registrarme", exact: true }).click();
    await this.fillRegisterForm(overrides);
    await this.registerSubmit.click();
  }

  async login({ username = AUTH_USER.username, password = AUTH_PASSWORD } = {}) {
    await this.page.getByLabel("Usuario", { exact: true }).fill(username);
    await this.page.getByLabel("Contraseña", { exact: true }).fill(password);
    await this.loginSubmit.click();
  }

  async goto() {
    // El stub va antes del goto: así ninguna petición real se escapa.
    await stubAuth(this.page);
    await this.page.goto("/");
    // La app abre en la landing (logo animado + "Empezar"); la bienvenida es la segunda pantalla.
    await this.page.getByRole("button", { name: "Empezar" }).click();
    // La encuesta ya exige cuenta: el camino real pasa por el registro.
    await this.register();
    await this.fillName();
    await expect(this.page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toBeVisible();
  }

  /**
   * Primer paso de la encuesta: nombre y apellidos. Los apellidos son
   * opcionales en la app, pero se llenan aquí porque son los que terminan
   * impresos en el reverso de la tarjeta.
   */
  async fillName({ name = "Carlos Alberto", lastName = "Tabares Quiroz" } = {}) {
    await expect(this.page.getByRole("heading", { name: "¿Cómo te llamas?" })).toBeVisible();
    await this.page.getByRole("textbox", { name: "Tu nombre (o nombres)" }).fill(name);
    await this.page.getByRole("textbox", { name: "Tus apellidos" }).fill(lastName);
    await this.page.getByRole("button", { name: "Continuar" }).click();
  }

  async pickCategory(label: string) {
    await this.page.getByRole("button", { name: new RegExp(label) }).click();
  }

  /**
   * Responde todas las preguntas de la categoría con el mismo valor.
   * El número depende de la categoría (6 universales + las suyas), así que
   * itera hasta que la pantalla cambia en vez de asumir un total fijo.
   */
  async answerAllQuestions(answer: "Sí" | "No") {
    const button = this.page.getByRole("button", { name: answer, exact: true });
    for (let i = 0; i < 20; i++) {
      if (!(await button.isVisible().catch(() => false))) break;
      await button.click();
    }
    await expect(this.page.getByText(/cómo es una semana normal/)).toBeVisible();
  }

  async describeWeekAsText(text: string) {
    await this.weekTextarea.fill(text);
    await this.continueButton.click();
  }

  /** Selecciona días por posición (L M M J V S D — las etiquetas se repiten). */
  async pickDays(indexes: number[]) {
    const bubbles = this.page.locator(".bubble-grid button");
    for (const i of indexes) await bubbles.nth(i).click();
    await this.continueButton.click();
  }

  async pickEmployees(label: string) {
    await this.page.getByRole("button", { name: label, exact: true }).click();
  }

  async finish(city: string) {
    await this.cityInput.fill(city);
    await this.page.getByRole("button", { name: "Terminar" }).click();
  }

  /** Camino completo hasta justo después de mandar el POST. */
  async completeSurvey({ city = "Monterrey" }: { city?: string } = {}) {
    await this.goto();
    await this.fillSurvey({ city });
  }

  /** Sólo los pasos de la encuesta (ya en "Selecciona tu modelo de negocio"). */
  async fillSurvey({ city = "Monterrey" }: { city?: string } = {}) {
    await this.pickCategory("Comida y bebidas");
    await this.answerAllQuestions("Sí");
    await this.describeWeekAsText("Los lunes recibo mercancía y los fines de semana vendo más.");
    await this.pickDays([0, 1]);
    await this.pickEmployees("Solo yo");
    await this.finish(city);
  }

  // --- pantalla final -------------------------------------------------------
  get successTitle() {
    return this.page.getByRole("heading", { name: /¡Listo!/ });
  }
  get failureTitle() {
    return this.page.getByText("No se pudo guardar");
  }
  get retryButton() {
    return this.page.getByRole("button", { name: "Reintentar" });
  }
  get accountButton() {
    return this.page.getByRole("button", { name: "Ir a mi cuenta" });
  }
  get errorMessage() {
    return this.page.locator(".ob-error");
  }
}
