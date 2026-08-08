import type { ProviderCatalog, ProviderPlatform } from "@/lib/api";

const operationalStatuses = new Set([
  "implemented_not_verified",
  "verified_in_development",
  "production_ready",
]);

export function plannedPlatforms(catalog: ProviderCatalog): ProviderPlatform[] {
  return catalog.items
    .filter((provider) => provider.status === "planned")
    .flatMap((provider) => provider.platforms);
}

export function implementedConnectedImagePlatforms(catalog: ProviderCatalog) {
  return catalog.items
    .filter((provider) => provider.enabled && operationalStatuses.has(provider.status))
    .flatMap((provider) =>
      provider.platforms.map((platform) => ({
        ...platform,
        provider: provider.provider,
      })),
    )
    .filter((platform) =>
      operationalStatuses.has(platform.status) && platform.implemented && platform.connected,
    )
    .filter((platform) => platform.capabilities.supports_single_image)
    .map((platform) => ({
      provider: platform.provider,
      platform: platform.platform,
      displayName: platform.display_name,
      supportsText: platform.capabilities.supports_text,
      supportsSingleImage: platform.capabilities.supports_single_image,
    }));
}
