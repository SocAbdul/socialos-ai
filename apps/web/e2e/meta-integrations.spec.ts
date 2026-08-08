import { expect, test } from "@playwright/test";

test("Meta integrations expose only supported connection choices", async ({ page }) => {
  await page.goto("/integrations");
  await expect(page.getByRole("heading", { name: "Cuentas conectadas" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Facebook" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Instagram" })).toBeVisible();
  for (const platform of ["LinkedIn", "YouTube", "TikTok", "Reddit"]) {
    await expect(page.getByRole("heading", { name: platform })).toBeVisible();
  }
  await expect(page.getByText("Próximamente")).toHaveCount(4);
  await expect(page.getByRole("button", { name: /Connect (LinkedIn|YouTube|TikTok|Reddit)/ })).toHaveCount(0);
  await expect(page.getByText(/tokens are never shown/i)).toBeVisible();
  await expect(page.getByText(/Reels|Stories|carousel/i)).toHaveCount(0);
});

test("Meta integrations have no horizontal overflow on mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-390", "Mobile-only viewport assertion");
  await page.goto("/integrations");
  const dimensions = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBe(dimensions.client);
  await expect(page.getByText("Próximamente")).toHaveCount(4);
});

test("blocked popup offers a fresh same-window continuation", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "mobile-390", "Mobile uses full-page redirect by design");
  await page.goto("/integrations");
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    Object.defineProperty(window, "open", { configurable: true, value: () => null });
  });
  await page.getByRole("button", { name: "Connect Facebook" }).click();
  await expect(page.getByRole("button", { name: "Continuar en esta ventana" })).toBeVisible();
});

test("multiple connections have scoped actions and accessible disconnect confirmation", async ({ page }) => {
  test.skip(
    process.env.NEXT_PUBLIC_DEMO_MODE === "false",
    "Fixture connections are available only in demo mode.",
  );
  await page.goto("/integrations?fixture=connected");
  await expect(page.getByText("Kinetic Mobiles Madrid", { exact: true })).toBeVisible();
  await expect(page.getByText("Kinetic Mobiles Valencia", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Validate" })).toHaveCount(2);
  await page.waitForTimeout(250);
  await page.getByRole("button", { name: "Disconnect from SocialOS" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Desconectar de SocialOS" });
  await expect(dialog).toContainText("Las publicaciones anteriores permanecerán en tu historial");
  await expect(dialog.getByRole("button", { name: "Cancelar" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Desconectar de SocialOS" })).toBeVisible();
});
