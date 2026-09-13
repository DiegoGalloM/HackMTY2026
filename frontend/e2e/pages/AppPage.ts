import { expect, type Page } from "@playwright/test";

/**
 * Page Object de la app principal (ya con sesión): barra inferior, Cuenta,
 * Más. Selectores por rol y texto visible, igual que OnboardingPage.
 */
export class AppPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  get nav() {
    return this.page.getByRole("navigation", { name: "Navegación principal" });
  }

  /** Cuenta: el saludo con el primer nombre de la encuesta. */
  greeting(firstName: string) {
    return this.page.getByText(`Hola ${firstName}!`);
  }

  /** La lección de Cash Insight disparada por la encuesta (categoría + respuestas). */
  get cashInsight() {
    return this.page.locator(".cash-insight-card").first();
  }

  async openTab(label: "Cuenta" | "Vender" | "Análisis" | "Compras" | "Más") {
    await this.nav.getByRole("link", { name: label }).click();
  }

  /** "Más → Cerrar sesión": vuelve a la bienvenida sin nada de la cuenta en el dispositivo. */
  async logout() {
    await this.openTab("Más");
    await this.page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(this.page.getByRole("heading", { name: /Tu negocio.*en tus manos/i })).toBeVisible();
  }

  async expectOnAccount() {
    await expect(this.nav).toBeVisible();
    await expect(this.page.locator(".reference-card img")).toHaveAttribute("src", /capital-one-main-page-card/);
  }

  async expectNotInSurvey() {
    await expect(this.page.getByRole("heading", { name: "¿Cómo te llamas?" })).toHaveCount(0);
    await expect(this.page.getByRole("heading", { name: "Selecciona tu modelo de negocio" })).toHaveCount(0);
  }
}
