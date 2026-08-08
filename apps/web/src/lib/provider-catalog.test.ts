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
] };

describe("provider catalog selectors", () => {
  it("only enables implemented, connected and media-compatible composer targets", () => {
    expect(implementedConnectedImagePlatforms(catalog)).toEqual([{
      platform: "facebook",
      displayName: "Facebook",
      supportsText: true,
      supportsSingleImage: true,
    }]);
  });

  it("keeps planned platforms discoverable without making them operational", () => {
    expect(plannedPlatforms(catalog).map((item) => item.platform)).toEqual(["linkedin"]);
    expect(plannedPlatforms(catalog)[0].implemented).toBe(false);
  });
});
