import { expect, type Locator, type Page } from "@playwright/test";

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

  async goto() {
    await this.page.goto("/");
    // La app abre en la landing (logo animado + "Empezar"); la bienvenida es la segunda pantalla.
    await this.page.getByRole("button", { name: "Empezar" }).click();
    await this.page.getByRole("button", { name: "Registrarme", exact: true }).click();
    await this.page.getByRole("button", { name: "Comenzar mi encuesta" }).click();
    await expect(this.page.getByText("Selecciona tu modelo de negocio")).toBeVisible();
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
