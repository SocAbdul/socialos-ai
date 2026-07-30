import { expect, test } from "@playwright/test";

async function reloadUntilText(page: import("@playwright/test").Page, text: string) {
  for (let index = 0; index < 10; index += 1) {
    await page.reload();
    if (await page.getByText(text).first().isVisible().catch(() => false)) return;
    await page.waitForTimeout(1_000);
  }
  await expect(page.getByText(text).first()).toBeVisible();
}

test.describe("backend-connected local publishing walkthrough", () => {
  test.setTimeout(90_000);

  test.skip(
    process.env.NEXT_PUBLIC_DEMO_MODE !== "false",
    "Requires the real local stack with NEXT_PUBLIC_DEMO_MODE=false",
  );

  test("creates local accounts, content, publication, attempts, retry and cancel", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("Local product walkthrough")).toBeVisible();

    await page.getByRole("button", { name: /local accounts/i }).click();
    await expect(page.getByText("Local development accounts are ready.")).toBeVisible();
    await expect(page.locator("#create-post").getByText("Local Facebook Page")).toBeVisible();
    await expect(page.locator("#create-post").getByText("Local Instagram Business")).toBeVisible();

    await page.getByRole("button", { name: "Adapt and create publication" }).click();
    await expect(page.getByText("Publication created and ready.")).toBeVisible();
    await expect(page.getByText("Publication diagnostics")).toBeVisible();

    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    await expect(page.getByText("Publication scheduled 15 minutes from now.")).toBeVisible();
    await expect(page.getByText("scheduled").first()).toBeVisible();

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Publication cancelled.")).toBeVisible();
    await expect(page.getByText("cancelled").first()).toBeVisible();

    await page.getByLabel("Platform").selectOption("facebook");
    await page.getByLabel("Original content").fill(
      "Kinetic Mobiles can diagnose battery, charging and screen issues before lunch for local business fleets.",
    );
    await page.getByRole("button", { name: "Adapt and create publication" }).click();
    await expect(page.getByText("Publication created and ready.")).toBeVisible();
    await page.getByRole("button", { name: "Publish now" }).click();
    await expect(page.getByText("Publication queued for local worker.")).toBeVisible();
    await reloadUntilText(page, "succeeded");
    await expect(page.getByText("Open local URL")).toBeVisible();

    await page.getByLabel("Simulate retryable provider error").check();
    await page.getByLabel("Original content").fill(
      "Kinetic Mobiles is testing safe retry handling for local social publishing.",
    );
    await page.getByRole("button", { name: "Adapt and create publication" }).click();
    await expect(page.getByText("Publication created and ready.")).toBeVisible();
    await page.getByRole("button", { name: "Publish now" }).click();
    await expect(page.getByText("Publication queued for local worker.")).toBeVisible();
    await reloadUntilText(page, "failed retryable");
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(page.getByText("Retry queued for local worker.")).toBeVisible();
  });

  test("real walkthrough is usable on a mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 1100 });
    await page.goto("/");

    await expect(page.getByText("Local product walkthrough")).toBeVisible();
    const viewport = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth);
  });
});
