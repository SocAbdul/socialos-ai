import { describe, expect, it } from "vitest";

import type { ProviderCatalog } from "@/lib/api";
import { implementedConnectedImagePlatforms, plannedPlatforms } from "./provider-catalog";

const capabilities = {
  supports_text: false, supports_single_image: false, supports_multiple_images: false,
  supports_video: false, supports_reels: false, supports_stories: false,
  supports_scheduling: false, supports_delete: false, supports_short_video: false,
  supports_comments: false, supports_analytics: false, supports_mentions: false,
  supports_hashtags: false, supports_first_comment: false, requires_public_media_url: false,
  max_text_length: 0, supported_media_types: [], daily_publication_limit: null,
};
const catalog: ProviderCatalog = { items: [
  { provider: "meta", display_name: "Meta", status: "verified_in_development", enabled: true, platforms: [
    { platform: "facebook", display_name: "Facebook", description: "Pages", status: "verified_in_development", implemented: true, connected: true, api_capabilities: { ...capabilities, supports_single_image: true }, capabilities: { ...capabilities, supports_text: true, supports_single_image: true } },
    { platform: "instagram", display_name: "Instagram", description: "Professional", status: "verified_in_development", implemented: true, connected: false, api_capabilities: { ...capabilities, supports_single_image: true }, capabilities: { ...capabilities, supports_single_image: true } },
  ] },
  { provider: "linkedin", display_name: "LinkedIn", status: "planned", enabled: false, platforms: [
    { platform: "linkedin", display_name: "LinkedIn", description: "Professional", status: "planned", implemented: false, connected: false, api_capabilities: { ...capabilities, supports_text: true }, capabilities },
  ] },
  { provider: "future_provider", display_name: "Future Provider", status: "verified_in_development", enabled: true, platforms: [
    { platform: "future_social", display_name: "Future Social", description: "Synthetic test target", status: "verified_in_development", implemented: true, connected: true, api_capabilities: { ...capabilities, supports_single_image: true }, capabilities: { ...capabilities, supports_single_image: true } },
  ] },
] };

describe("provider catalog selectors", () => {
  it("only enables implemented, connected and media-compatible composer targets", () => {
    expect(implementedConnectedImagePlatforms(catalog).map((item) => item.platform)).toEqual([
      "facebook",
      "future_social",
    ]);
  });

  it.each([
    ["not implemented", { implemented: false }],
    ["not connected", { connected: false }],
    ["not image capable", { capabilities: { ...capabilities, supports_single_image: false } }],
  ])("excludes a future provider when it is %s", (_name, override) => {
    const future = catalog.items.find((item) => item.provider === "future_provider")!;
    const changed: ProviderCatalog = {
      items: catalog.items.map((provider) => provider.provider === "future_provider"
        ? { ...provider, platforms: [{ ...future.platforms[0], ...override }] }
        : provider),
    };
    expect(implementedConnectedImagePlatforms(changed).map((item) => item.platform)).not.toContain("future_social");
  });

  it("keeps every planned provider out of composer eligibility", () => {
    const plannedNames = ["linkedin", "youtube", "tiktok", "reddit"];
    const planned: ProviderCatalog = {
      items: plannedNames.map((provider) => ({
        provider, display_name: provider, status: "planned", enabled: true,
        platforms: [{ platform: provider, display_name: provider, description: "planned", status: "planned", implemented: false, connected: true, api_capabilities: { ...capabilities, supports_single_image: true }, capabilities: { ...capabilities, supports_single_image: true } }],
      })),
    };
    expect(implementedConnectedImagePlatforms(planned)).toEqual([]);
  });

  it("keeps planned platforms discoverable without making them operational", () => {
    expect(plannedPlatforms(catalog).map((item) => item.platform)).toEqual(["linkedin"]);
    expect(plannedPlatforms(catalog)[0].implemented).toBe(false);
  });
});
