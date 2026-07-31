import { describe, expect, it } from "vitest";

import { validateWalkthrough } from "./walkthrough-validation";

function formData(overrides: Record<string, string> = {}) {
  const data = new FormData();
  const values = {
    workspaceId: "f6b262d4-1524-4e63-aa06-20d4756974e7",
    brandName: "Kinetic Mobiles",
    campaignName: "Same-day repair launch",
    voice: "Helpful and practical",
    audience: "Local professionals",
    contentBody: "Same-day screen repairs are now available.",
    platform: "instagram",
    mediaUrl: "https://media.example.com/repair.jpg",
    contentType: "image/jpeg",
    checksumSha256: "a".repeat(64),
    ...overrides,
  };
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

describe("walkthrough validation", () => {
  it("trims and accepts valid values", () => {
    const result = validateWalkthrough(
      formData({ brandName: "  Kinetic Mobiles  " }),
    );
    expect(result.data?.brandName).toBe("Kinetic Mobiles");
    expect(result.errors).toEqual({});
  });

  it("reports every required field before any request", () => {
    const result = validateWalkthrough(
      formData({
        brandName: " ",
        campaignName: "",
        voice: " ",
        audience: "",
        contentBody: " ",
        mediaUrl: "",
      }),
    );
    expect(result.data).toBeNull();
    expect(Object.keys(result.errors)).toEqual([
      "brandName",
      "campaignName",
      "voice",
      "audience",
      "contentBody",
      "mediaUrl",
    ]);
  });

  it.each(["not-a-valid-url", "ftp://example.com/image.jpg"])(
    "rejects unsupported media URL %s",
    (mediaUrl) => {
      const result = validateWalkthrough(formData({ mediaUrl }));
      expect(result.errors.mediaUrl).toBe(
        "Enter a complete http or https URL.",
      );
    },
  );
});
