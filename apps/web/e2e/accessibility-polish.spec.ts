import { expect, test } from "@playwright/test";

async function openDashboard(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
}

test.describe("final preview accessibility polish", () => {
  test("keyboard focus remains visible and refresh is single-submit", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Desktop keyboard check.");
    test.skip(
      process.env.NEXT_PUBLIC_DEMO_MODE !== "false",
      "Refresh requires the backend-connected local walkthrough.",
    );
    await openDashboard(page);

    const notifications = page.getByRole("button", { name: "Notifications" });
    const createPost = page.getByRole("link", { name: "Create post" });
    await notifications.focus();
    await expect(notifications).toBeFocused();
    expect(
      await notifications.evaluate(
        (element) => getComputedStyle(element).boxShadow,
      ),
    ).not.toBe("none");
    await page.keyboard.press("Tab");
    await expect(createPost).toBeFocused();
    expect(
      await createPost.evaluate(
        (element) => getComputedStyle(element).boxShadow,
      ),
    ).not.toBe("none");
    await page.keyboard.press("Shift+Tab");
    await expect(notifications).toBeFocused();

    const accountsButton = page.getByRole("button", {
      name: /local accounts/i,
    });
    if ((await accountsButton.textContent())?.includes("Create")) {
      await accountsButton.click();
      await expect(
        page.getByText("Local development accounts are ready."),
      ).toBeVisible();
    }
    const facebookBefore = await page
      .getByText("Local Facebook Page", { exact: true })
      .count();
    const instagramBefore = await page
      .getByText("Local Instagram Business", { exact: true })
      .count();
    let delayed = false;
    await page.route("**/*", async (route) => {
      if (!delayed && route.request().method() === "POST") {
        delayed = true;
        await new Promise((resolve) => setTimeout(resolve, 1_500));
      }
      await route.continue();
    });
    const refresh = page.getByRole("button", {
      name: "Refresh local accounts",
    });
    const response = page.waitForResponse(
      (candidate) => candidate.request().method() === "POST",
    );
    const click = refresh.dblclick();
    const pending = page.getByRole("button", { name: "Refreshing..." });
    await expect(pending).toBeDisabled();
    await expect(pending).toHaveAttribute("aria-disabled", "true");
    await Promise.all([response, click]);
    await page.waitForLoadState("networkidle");
    await page.unroute("**/*");
    await expect(
      page.getByRole("button", { name: "Refresh local accounts" }),
    ).toBeEnabled();
    expect(
      await page.getByText("Local Facebook Page", { exact: true }).count(),
    ).toBe(facebookBefore);
    expect(
      await page.getByText("Local Instagram Business", { exact: true }).count(),
    ).toBe(instagramBefore);
  });

  test("mobile controls meet the 44px target without overflow", async ({
    page,
  }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-390",
      "Dedicated mobile check.",
    );
    test.skip(
      process.env.NEXT_PUBLIC_DEMO_MODE !== "false",
      "Mobile controls belong to the backend-connected walkthrough.",
    );
    await openDashboard(page);
    const openNavigation = page.getByRole("button", {
      name: "Open navigation",
    });
    const notifications = page.getByRole("button", { name: "Notifications" });
    for (const control of [openNavigation, notifications]) {
      const box = await control.boundingBox();
      expect(box?.width).toBeGreaterThanOrEqual(44);
      expect(box?.height).toBeGreaterThanOrEqual(44);
    }
    await openNavigation.click();
    await expect(
      page.getByRole("dialog", { name: "Navigation" }),
    ).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBe(dimensions.clientWidth);
  });
});
