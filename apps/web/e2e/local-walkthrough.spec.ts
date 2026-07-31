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

async function fillWalkthrough(
  page: import("@playwright/test").Page,
  overrides: {
    content?: string;
    mediaUrl?: string;
    platform?: "facebook" | "instagram";
  } = {},
) {
  await page.getByLabel("Brand Profile").fill("Kinetic Mobiles");
  await page.getByLabel("Campaign").fill("Same-day repair launch");
  await page
    .getByLabel("Brand voice")
    .fill("Helpful, precise, practical and confident. Never gimmicky.");
  await page
    .getByLabel("Audience")
    .fill("Local professionals and families who need reliable phone repairs.");
  await page
    .getByLabel("Original content")
    .fill(
      overrides.content ??
        "Kinetic Mobiles now offers same-day screen repairs for busy professionals in Valencia.",
    );
  await page
    .getByLabel("Platform")
    .selectOption(overrides.platform ?? "instagram");
  await page
    .getByLabel("Media Asset URL")
    .fill(
      overrides.mediaUrl ??
        "https://media.local.socialos.invalid/kinetic-mobiles/same-day-screen-repair.jpg",
    );
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

    const inventoryIds = [
      "inventory-brand-profiles",
      "inventory-campaigns",
      "inventory-content-items",
      "inventory-media-assets",
    ];
    const inventoryBefore = await Promise.all(
      inventoryIds.map((id) =>
        page.getByTestId(id).locator("span").textContent(),
      ),
    );

    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(page.getByText("Brand Profile is required.")).toBeVisible();
    await expect(page.getByText("Campaign is required.")).toBeVisible();
    await expect(page.getByText("Original content is required.")).toBeVisible();
    await expect(page.getByLabel("Brand Profile")).toBeFocused();
    await expect(page.getByLabel("Brand Profile")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    const inventoryAfter = await Promise.all(
      inventoryIds.map((id) =>
        page.getByTestId(id).locator("span").textContent(),
      ),
    );
    expect(inventoryAfter).toEqual(inventoryBefore);

    await fillWalkthrough(page, { mediaUrl: "not-a-valid-url" });
    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .click();
    await expect(
      page.getByText("Enter a complete http or https URL."),
    ).toBeVisible();
    await expect(page.getByLabel("Media Asset URL")).toBeFocused();
    await expect(page.getByLabel("Brand Profile")).toHaveValue(
      "Kinetic Mobiles",
    );
    await page
      .getByLabel("Media Asset URL")
      .fill(
        "https://media.local.socialos.invalid/kinetic-mobiles/same-day-screen-repair.jpg",
      );

    let delayedSubmission = false;
    const delayedSubmissionHandler = async (
      route: import("@playwright/test").Route,
    ) => {
      if (!delayedSubmission && route.request().method() === "POST") {
        delayedSubmission = true;
        await new Promise((resolve) => setTimeout(resolve, 2_000));
      }
      await route.continue();
    };
    await page.route("**/*", delayedSubmissionHandler);
    const accountsButton = page.getByRole("button", {
      name: /local accounts/i,
    });
    const loadingWasVisible = page.waitForFunction(() => {
      const button = [...document.querySelectorAll("button")].find(
        (candidate) =>
          /Creating accounts|Refreshing/.test(candidate.textContent ?? ""),
      );
      return Boolean(
        button?.hasAttribute("disabled") &&
        /Creating accounts|Refreshing/.test(button.textContent ?? ""),
      );
    });
    await Promise.all([loadingWasVisible, accountsButton.click()]);
    await expect(
      page.getByText("Local development accounts are ready."),
    ).toBeVisible();
    await page.unroute("**/*", delayedSubmissionHandler);
    await expect(
      page.locator("#create-post").getByText("Local Facebook Page"),
    ).toBeVisible();
    await expect(
      page.locator("#create-post").getByText("Local Instagram Business"),
    ).toBeVisible();

    let delayedRefresh = false;
    const delayedRefreshHandler = async (
      route: import("@playwright/test").Route,
    ) => {
      if (!delayedRefresh && route.request().method() === "POST") {
        delayedRefresh = true;
        await new Promise((resolve) => setTimeout(resolve, 1_500));
      }
      await route.continue();
    };
    await page.route("**/*", delayedRefreshHandler);
    const refreshButton = page.getByRole("button", {
      name: "Refresh local accounts",
    });
    const refreshPending = page.waitForFunction(() => {
      const button = [...document.querySelectorAll("button")].find(
        (candidate) => candidate.textContent?.includes("Refreshing"),
      );
      return Boolean(button?.hasAttribute("disabled"));
    });
    const refreshResponse = page.waitForResponse(
      (response) => response.request().method() === "POST",
    );
    await Promise.all([refreshPending, refreshResponse, refreshButton.click()]);
    await page.waitForLoadState("networkidle");
    await page.unroute("**/*", delayedRefreshHandler);
    await fillWalkthrough(page);

    await page
      .getByRole("button", { name: "Adapt and create publication" })
      .dblclick();
    await expect(
      page.getByText("Publication created and ready."),
    ).toBeVisible();
    await expect(page.getByText("AI cost: €0.00")).toBeVisible();
    await expect(page.getByText("Publication diagnostics")).toBeVisible();
    await expect(
      page.getByTestId("inventory-brand-profiles").locator("span"),
    ).toHaveText(String(Number(inventoryBefore[0]) + 1));

    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    await expect(
      page.getByText("Publication scheduled 15 minutes from now."),
    ).toBeVisible();
    await expect(page.getByText("scheduled").first()).toBeVisible();

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Publication cancelled.")).toBeVisible();
    await expect(page.getByText("cancelled").first()).toBeVisible();

    await fillWalkthrough(page, {
      content:
        "Kinetic Mobiles can diagnose battery, charging and screen issues before lunch for local business fleets.",
      platform: "facebook",
    });
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

    await fillWalkthrough(page, {
      content:
        "Kinetic Mobiles is testing safe retry handling for local social publishing.",
      platform: "facebook",
    });
    await page.getByLabel(/Simulate one retryable failure/).check();
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
    await reloadUntilText(page, "published");
    await expect(page.getByText("2 attempts", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Attempt 2" }).getByText("started"),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Attempt 2" }).getByText("succeeded"),
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
    await fillWalkthrough(page, {
      content: "Kinetic Mobiles prueba una publicación segura desde un móvil.",
      mediaUrl:
        "https://media.local.socialos.invalid/kinetic-mobiles/mobile-demo.jpg",
    });
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

    await fillWalkthrough(page, {
      content:
        "Kinetic Mobiles prueba la recuperación segura de publicaciones desde un móvil.",
      mediaUrl:
        "https://media.local.socialos.invalid/kinetic-mobiles/mobile-demo.jpg",
    });
    await page.getByLabel(/Simulate one retryable failure/).check();
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
    await reloadUntilText(page, "published");
    await expect(page.getByText("2 attempts", { exact: true })).toBeVisible();

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
