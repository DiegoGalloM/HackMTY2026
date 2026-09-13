import { expect, test } from "@playwright/test";

/** Entra a la app saltándose la encuesta: solo interesa la pantalla Cuenta. */
async function goToAccount(
  page: import("@playwright/test").Page,
  { name = "Carlos Alberto", lastName = "Tabares Quiroz" } = {},
) {
  await page.goto("/");
  await page.getByRole("button", { name: "Registrarme", exact: true }).click();
  await page.getByRole("button", { name: "Comenzar mi encuesta" }).click();
  await page.getByRole("textbox", { name: /Tu nombre/ }).fill(name);
  await page.getByRole("textbox", { name: /Tus apellidos/ }).fill(lastName);
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Saltar encuesta" }).click();
  await expect(page.locator(".business-card-surface")).toBeVisible();
}

test("la tarjeta se voltea y sus datos se copian al portapapeles", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await goToAccount(page);

  const trigger = page.getByRole("button", { name: /Ver los datos de la tarjeta/ });
  const numero = page.getByRole("button", { name: /Copiar número de tarjeta/ });
  const titular = page.getByRole("button", { name: /Copiar titular/ });

  await expect(numero).toHaveCount(0);
  await trigger.click();
  await expect(numero).toBeVisible();

  // Con el cursor encima la tarjeta se inclina en 3D: es el caso en el que el
  // hit-testing del navegador se desalinea si el reverso se pinta espejeado,
  // así que los clics se hacen justo ahí.
  const box = (await page.locator(".business-card-surface").boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.7);

  await numero.click();
  await expect(numero).toContainText("Copiado");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe("4147209388431234");

  await titular.click();
  await expect(titular).toContainText("Copiado");
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    "CARLOS ALBERTO TABARES QUIROZ",
  );

  // El frente no existe para el teclado ni para un lector de pantalla
  // mientras la tarjeta está volteada.
  await expect(trigger).toHaveCount(0);

  await page.getByRole("button", { name: "Voltear" }).click();
  await expect(trigger).toBeVisible();
  await expect(numero).toHaveCount(0);
});

test("tocar cualquier parte del reverso la regresa, menos los datos", async ({ page }) => {
  await goToAccount(page);

  const trigger = page.getByRole("button", { name: /Ver los datos de la tarjeta/ });
  const numero = page.getByRole("button", { name: /Copiar número de tarjeta/ });

  await trigger.click();
  await expect(numero).toBeVisible();

  // Un clic sobre un dato copia, no voltea.
  await numero.click();
  await expect(numero).toBeVisible();

  // Uno en la franja de arriba, fuera de los datos, sí voltea.
  const box = (await page.locator(".business-card-surface").boundingBox())!;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.12);
  await expect(trigger).toBeVisible();
  await expect(numero).toHaveCount(0);
});

test("la tarjeta se voltea con el teclado y Escape la regresa", async ({ page }) => {
  await goToAccount(page);

  const trigger = page.getByRole("button", { name: /Ver los datos de la tarjeta/ });
  const numero = page.getByRole("button", { name: /Copiar número de tarjeta/ });

  await trigger.press("Enter");
  await expect(numero).toBeFocused();
  // Escape a media animación también cuenta: la tarjeta se regresa igual.
  await numero.press("Escape");
  await expect(trigger).toBeFocused();
});

test("el saludo usa el primer nombre y la tarjeta el nombre completo", async ({ page }) => {
  await goToAccount(page, { name: "Ana María", lastName: "Ruiz Peña" });

  await expect(page.getByText("Hola Ana!")).toBeVisible();
  await page.getByRole("button", { name: /Ver los datos de la tarjeta/ }).click();
  await expect(page.getByRole("button", { name: /Copiar titular/ })).toContainText(
    "ANA MARÍA RUIZ PEÑA",
  );
});

test("sin apellidos la tarjeta muestra solo el nombre", async ({ page }) => {
  await goToAccount(page, { name: "Carlos", lastName: "" });

  await expect(page.getByText("Hola Carlos!")).toBeVisible();
  await page.getByRole("button", { name: /Ver los datos de la tarjeta/ }).click();
  await expect(
    page.getByRole("button", { name: "Copiar titular: CARLOS", exact: true }),
  ).toBeVisible();
});

test("sin nombre la tarjeta dice USUARIO", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Explorar la demo/ }).click();

  await expect(page.getByText("Hola Usuario!")).toBeVisible();
  await page.getByRole("button", { name: /Ver los datos de la tarjeta/ }).click();
  await expect(
    page.getByRole("button", { name: "Copiar titular: USUARIO", exact: true }),
  ).toBeVisible();
});

test("la tarjeta de la bienvenida no se voltea", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".business-card-surface")).toBeVisible();
  await expect(page.getByRole("button", { name: /Ver los datos de la tarjeta/ })).toHaveCount(0);
});
