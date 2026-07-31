import { expect, test } from "@playwright/test";

async function reloadUntilText(
  page: import("@playwright/test").Page,
  text: string,
) {
  for (let index = 0; index < 10; index += 1) {
    await page.reload();
    if (
      await page
        .getByText(text)
        .filter({ visible: true })
        .first()
        .isVisible()
        .catch(() => false)
    )
      return;
    await page.waitForTimeout(1_000);
  }
  await expect(
    page.getByText(text).filter({ visible: true }).first(),
  ).toBeVisible();
}

async function openWalkthrough(page: import("@playwright/test").Page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.goto("/", { waitUntil: "networkidle" });
      await expect(page.getByText("Local product walkthrough")).toBeVisible();
      return;
    } catch (error) {
      if (attempt === 2) throw error;
      await page.waitForTimeout(1_000);
    }
  }
}

test.describe("backend-connected local publishing walkthrough", () => {
  test.setTimeout(120_000);

  test.skip(
    process.env.NEXT_PUBLIC_DEMO_MODE !== "false",
    "Requires the real local stack with NEXT_PUBLIC_DEMO_MODE=false",
  );

  test("creates local accounts, content, publication, attempts, retry and cancel", async ({
    page,
  }, testInfo) => {
    test.skip(
      testInfo.project.name !== "chromium",
      "Desktop walkthrough runs in Chromium.",
    );
    await openWalkthrough(page);

    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

    let delayedSubmission = false;
    await page.route("**/*", async (route) => {
      if (!delayedSubmission && route.request().method() === "POST") {
        delayedSubmission = true;
        await new Promise((resolve) => setTimeout(resolve, 2_000));
      }
      await route.continue();
    });
    const accountsButton = page.getByRole("button", {
      name: /local accounts/i,
    });
    const loadingWasVisible = page.waitForFunction(() => {
      const button = [...document.querySelectorAll("button")].find(
        (candidate) => /accounts/i.test(candidate.textContent ?? ""),
      );
      return Boolean(
        button?.hasAttribute("disabled") &&
        /Creating accounts|Refreshing accounts/.test(button.textContent ?? ""),
      );
    });
    await Promise.all([loadingWasVisible, accountsButton.click()]);
    await expect(
      page.getByText("Local development accounts are ready."),
    ).toBeVisible();
    await page.unroute("**/*");
    await expect(
      page.locator("#create-post").getByText("Local Facebook Page"),
    ).toBeVisible();
    await expect(
      page.locator("#create-post").getByText("Local Instagram Business"),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.getByText("Publication created and ready."),
    ).toBeVisible();
    await expect(page.getByText("Publication diagnostics")).toBeVisible();

    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    await expect(
      page.getByText("Publication scheduled 15 minutes from now."),
    ).toBeVisible();
    await expect(page.getByText("scheduled").first()).toBeVisible();

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Publication cancelled.")).toBeVisible();
    await expect(page.getByText("cancelled").first()).toBeVisible();

    await page.getByLabel("Platform").selectOption("facebook");
    await page
      .getByLabel("Original content")
      .fill(
        "Kinetic Mobiles can diagnose battery, charging and screen issues before lunch for local business fleets.",
      );
    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.getByText("Publication created and ready."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Publish now" }).click();
    await expect(
      page.getByText("Publication queued for local worker."),
    ).toBeVisible();
    await reloadUntilText(page, "succeeded");
    await expect(page.getByText("1 attempt", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Attempt 1" }).getByText("started"),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Attempt 1" }).getByText("succeeded"),
    ).toBeVisible();
    await expect(page.getByText("Open local URL")).toBeVisible();

    await page.getByLabel("Simulate retryable provider error").check();
    await page
      .getByLabel("Original content")
      .fill(
        "Kinetic Mobiles is testing safe retry handling for local social publishing.",
      );
    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.getByText("Publication created and ready."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Publish now" }).click();
    await expect(
      page.getByText("Publication queued for local worker."),
    ).toBeVisible();
    await reloadUntilText(page, "failed retryable");
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(
      page.getByText("Retry queued for local worker."),
    ).toBeVisible();
    await reloadUntilText(page, "2 attempts");
    await expect(
      page.getByRole("region", { name: "Attempt 2" }).getByText("started"),
    ).toBeVisible();
  });

  test("real walkthrough is usable end to end on a 390px mobile viewport", async ({
    page,
  }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-390",
      "Mobile walkthrough runs in its dedicated project.",
    );
    await openWalkthrough(page);
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(
      page.getByRole("dialog", { name: "Navigation" }),
    ).toBeVisible();
    const mobileNavigation = page.getByRole("dialog", { name: "Navigation" });
    await expect(
      mobileNavigation.getByTitle("Content is coming soon"),
    ).toHaveAttribute("aria-disabled", "true");
    await mobileNavigation.getByRole("link", { name: "Create" }).click();
    await expect(page.locator("#create-post")).toBeInViewport();

    await page.getByRole("button", { name: /local accounts/i }).click();
    await expect(
      page.getByText("Local development accounts are ready."),
    ).toBeVisible();
    await page.getByLabel("Platform").selectOption("instagram");
    await page
      .getByLabel("Media Asset URL")
      .fill(
        "https://media.local.socialos.invalid/kinetic-mobiles/mobile-demo.jpg",
      );
    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.getByText("Publication created and ready."),
    ).toBeVisible();
    await expect(page.getByText("Publication diagnostics")).toBeVisible();

    const scheduleButton = page.getByRole("button", {
      name: "Schedule",
      exact: true,
    });
    const scheduleBox = await scheduleButton.boundingBox();
    expect(scheduleBox?.height).toBeGreaterThanOrEqual(40);
    await scheduleButton.click();
    await expect(
      page.getByText("Publication scheduled 15 minutes from now."),
    ).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Publication cancelled.")).toBeVisible();

    await page.getByLabel("Simulate retryable provider error").check();
    await page
      .getByLabel("Original content")
      .fill(
        "Kinetic Mobiles prueba la recuperación segura de publicaciones desde un móvil.",
      );
    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.locator("#publication-detail").getByText("Pensado para el feed"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Publish now" }).click();
    await reloadUntilText(page, "failed retryable");
    await expect(
      page.getByText(/simulated a retryable network error/i).first(),
    ).toBeVisible();
    await expect(page.getByRole("region", { name: "Attempt 1" })).toBeVisible();
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(
      page.getByText("Retry queued for local worker."),
    ).toBeVisible();

    const viewport = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth);

    await page.screenshot({
      fullPage: true,
      path: testInfo.outputPath("mobile-390-walkthrough.png"),
    });
  });
});
