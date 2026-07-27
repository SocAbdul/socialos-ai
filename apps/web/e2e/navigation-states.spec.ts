import { expect, test } from "@playwright/test";

test("unknown routes show a useful recovery path", async ({ page }) => {
  await page.goto("/workspace/does-not-exist");

  await expect(page.getByRole("heading", { name: "This page is not in your workspace." })).toBeVisible();
  await expect(page.getByText("The link may be outdated")).toBeVisible();

  await page.getByRole("link", { name: "Back to dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Review the Meta publishing flow" })).toBeVisible();
});
