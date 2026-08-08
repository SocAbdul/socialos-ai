import type { ProviderCatalog, ProviderPlatform } from "@/lib/api";

export function plannedPlatforms(catalog: ProviderCatalog): ProviderPlatform[] {
  return catalog.items
    .filter((provider) => provider.status === "planned")
    .flatMap((provider) => provider.platforms);
}

export function implementedConnectedImagePlatforms(catalog: ProviderCatalog) {
  return catalog.items
    .filter((provider) => provider.enabled)
    .flatMap((provider) => provider.platforms)
    .filter((platform) => platform.implemented && platform.connected)
    .filter((platform) => platform.capabilities.supports_single_image)
    .filter((platform) => platform.platform === "facebook" || platform.platform === "instagram")
    .map((platform) => ({
      platform: platform.platform as "facebook" | "instagram",
      displayName: platform.display_name,
      supportsText: platform.capabilities.supports_text,
      supportsSingleImage: platform.capabilities.supports_single_image,
    }));
}
