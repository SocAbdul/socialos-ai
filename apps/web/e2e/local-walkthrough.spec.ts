import { expect, test, type Page } from "@playwright/test";

const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

async function openRealComposer(page: Page) {
  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByText("Local product walkthrough")).toBeVisible();
  const createAccounts = page.getByRole("button", { name: /Create local accounts/i });
  if (await createAccounts.isVisible().catch(() => false)) {
    await createAccounts.click();
    await expect(page.getByText("2 social accounts are available.")).toBeVisible();
  }
}

async function fillComposer(page: Page) {
  await page.getByLabel("Brand Profile").fill("Kinetic Mobiles");
  await page.getByLabel("Campaign").fill("Same-day repair launch");
  await page.getByLabel("Brand voice").fill("Helpful, precise and practical.");
  await page.getByLabel("Audience").fill("Local professionals and families.");
  await page
    .getByLabel("Base content")
    .fill("Same-day screen repairs are now available from Kinetic Mobiles.");
  await page.getByLabel("Facebook", { exact: true }).check();
  await page.getByLabel("Instagram", { exact: true }).check();
  await page.getByLabel("Facebook caption").fill("Your phone, repaired today.");
  await page
    .getByLabel("Instagram caption")
    .fill("Your phone, repaired today. #KineticMobiles");
  await page.getByLabel(/Drop a JPEG or PNG/).setInputFiles({
    name: "kinetic-repair.png",
    mimeType: "image/png",
    buffer: png,
  });
}

test.describe("real local multichannel composer", () => {
  test.setTimeout(120_000);
  test.skip(
    process.env.NEXT_PUBLIC_DEMO_MODE !== "false",
    "Requires Docker Compose with NEXT_PUBLIC_DEMO_MODE=false",
  );

  test("uploads, previews and creates independent Facebook and Instagram publications", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "Desktop flow runs once.");
    await openRealComposer(page);
    await fillComposer(page);

    await expect(page.getByAltText("Selected media preview")).toBeVisible();
    await expect(page.getByText("Facebook preview")).toBeVisible();
    await expect(page.getByText("Instagram preview")).toBeVisible();
    const publish = page.getByRole("button", { name: "Publish now" });
    await publish.click();
    await expect(page.getByText("2 platform publications queued.")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Your phone, repaired today.").first()).toBeVisible();
    await expect(page.getByText("Your phone, repaired today. #KineticMobiles").first()).toBeVisible();
  });

  test("mobile 390x844 supports upload, platform selection and preview without overflow", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-390", "Mobile regression runs once.");
    await openRealComposer(page);
    await fillComposer(page);
    await expect(page.getByRole("button", { name: "Publish now" })).toBeEnabled();
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBe(dimensions.clientWidth);
    await page.screenshot({ fullPage: true, path: testInfo.outputPath("multichannel-mobile-390.png") });
  });
});
