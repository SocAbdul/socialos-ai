import { expect, test } from "@playwright/test";

test("demo user can adapt, publish, inspect and retry", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Review the Meta publishing flow" })).toBeVisible();
  await expect(page.getByText("Kinetic Mobiles", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("@kineticmobiles")).toBeVisible();

  await page.getByRole("button", { name: "Adapt copy" }).click();
  await expect(page.getByText("Adapted copy is ready for both platforms.")).toBeVisible();

  await page.getByRole("button", { name: "Publish now" }).click();
  await expect(page.getByText("Publication sent successfully.")).toBeVisible();
  await expect(page.getByText("published").first()).toBeVisible();

  await page.getByText("uncertain").first().click();
  await expect(page.getByText("Reconcile with Meta before retrying")).toBeVisible();
  await page.getByRole("button", { name: "Retry safely" }).click();
  await expect(page.getByText("Retry completed without creating a duplicate.")).toBeVisible();

  await page.getByRole("button", { name: "Reset demo" }).click();
  await expect(page.getByText("Demo reset to the original Kinetic Mobiles data.")).toBeVisible();
});

test("demo dashboard fits a mobile viewport without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 1100 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Review the Meta publishing flow" })).toBeVisible();

  const viewport = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth);
});
