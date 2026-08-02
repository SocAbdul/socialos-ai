import { expect, test } from "@playwright/test";

test("Meta integrations expose only supported connection choices", async ({ page }) => {
  await page.goto("/integrations");
  await expect(page.getByRole("heading", { name: "Cuentas conectadas" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Facebook" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Instagram" })).toBeVisible();
  await expect(page.getByText(/tokens are never shown/i)).toBeVisible();
  await expect(page.getByText(/Reels|Stories|carousel|video/i)).toHaveCount(0);
});

test("Meta integrations have no horizontal overflow on mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-390", "Mobile-only viewport assertion");
  await page.goto("/integrations");
  const dimensions = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBe(dimensions.client);
});
