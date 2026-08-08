import { describe, expect, it } from "vitest";

import { validateWalkthrough } from "./walkthrough-validation";

function formData(overrides: Record<string, string> = {}, file: File | null = validPng()) {
  const data = new FormData();
  const values = {
    workspaceId: "f6b262d4-1524-4e63-aa06-20d4756974e7",
    submissionId: "submission-123456789",
    delivery: "now",
    brandName: "Kinetic Mobiles",
    campaignName: "Same-day repair launch",
    voice: "Helpful and practical",
    audience: "Local professionals",
    contentBody: "Same-day screen repairs are now available.",
    facebookCaption: "Fast repairs for Barcelona.",
    instagramCaption: "Fast repairs for Barcelona. #KineticMobiles",
    facebook: "on",
    ...overrides,
  };
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  if (file) data.set("mediaFile", file);
  return data;
}

function validPng() {
  return new File([new Uint8Array([137, 80, 78, 71])], "repair.png", { type: "image/png" });
}

describe("walkthrough validation", () => {
  it("trims and accepts a valid multichannel submission", () => {
    const result = validateWalkthrough(formData({ brandName: "  Kinetic Mobiles  " }));
    expect(result.data?.brandName).toBe("Kinetic Mobiles");
    expect(result.errors).toEqual({});
  });

  it("requires product data and a real image", () => {
    const result = validateWalkthrough(
      formData({ brandName: " ", campaignName: "", voice: " ", audience: "", contentBody: " " }, null),
    );
    expect(result.data).toBeNull();
    expect(result.errors).toMatchObject({
      brandName: "Brand Profile is required.",
      campaignName: "Campaign is required.",
      contentBody: "Original content is required.",
      mediaFile: "Choose a JPEG or PNG image.",
    });
  });

  it("requires at least one platform", () => {
    const data = formData();
    data.delete("facebook");
    expect(validateWalkthrough(data).errors.platforms).toBe(
      "Select at least one connected platform.",
    );
  });

  it("rejects unsupported image MIME types", () => {
    const gif = new File(["gif"], "repair.gif", { type: "image/gif" });
    expect(validateWalkthrough(formData({}, gif)).errors.mediaFile).toBe(
      "Only JPEG and PNG images are supported.",
    );
  });
});
