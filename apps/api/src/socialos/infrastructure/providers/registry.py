from dataclasses import dataclass
from enum import StrEnum

from socialos.application.posts.ports import SocialPublisher
from socialos.application.social.ports import SocialProviderCapabilities
from socialos.infrastructure.providers.errors import (
    CapabilityNotSupported,
    ProviderNotImplemented,
)


class ProviderStatus(StrEnum):
    NOT_IMPLEMENTED = "not_implemented"
    PLANNED = "planned"
    IMPLEMENTED_NOT_VERIFIED = "implemented_not_verified"
    VERIFIED_IN_DEVELOPMENT = "verified_in_development"
    PRODUCTION_READY = "production_ready"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    platform: str
    display_name: str
    description: str
    status: ProviderStatus
    implemented: bool
    api_capabilities: SocialProviderCapabilities
    socialos_capabilities: SocialProviderCapabilities


@dataclass(frozen=True, slots=True)
class ProviderDefinition:
    provider: str
    display_name: str
    status: ProviderStatus
    enabled: bool
    platforms: tuple[PlatformDefinition, ...]


class ProviderNotConfiguredError(LookupError):
    pass


class SocialProviderRegistry:
    """Runtime provider instances. Unknown providers never fall back silently."""

    def __init__(self, providers: list[SocialPublisher] | None = None) -> None:
        self._providers = {provider.provider_name: provider for provider in (providers or [])}

    def get(self, provider_name: str) -> SocialPublisher:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise ProviderNotConfiguredError(
                f"Social provider '{provider_name}' is not configured"
            ) from exc


class ProviderCatalog:
    def __init__(self, definitions: tuple[ProviderDefinition, ...]) -> None:
        self._definitions = {definition.provider: definition for definition in definitions}

    def list(self) -> tuple[ProviderDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, provider: str) -> ProviderDefinition:
        try:
            return self._definitions[provider]
        except KeyError as exc:
            raise ProviderNotConfiguredError(f"Unknown social provider '{provider}'") from exc

    def require_operational(self, provider: str, platform: str, capability: str) -> None:
        definition = self.get(provider)
        selected = next((item for item in definition.platforms if item.platform == platform), None)
        if selected is None:
            raise ProviderNotConfiguredError(f"Provider '{provider}' has no platform '{platform}'")
        if not definition.enabled or not selected.implemented:
            raise ProviderNotImplemented(f"Provider '{provider}' is not implemented")
        value = getattr(selected.socialos_capabilities, capability, None)
        if value is not True:
            raise CapabilityNotSupported(
                f"Capability '{capability}' is not supported for {provider}/{platform}"
            )


def _capabilities(
    *,
    text: bool = False,
    image: bool = False,
    multiple_images: bool = False,
    video: bool = False,
    short_video: bool = False,
    scheduling: bool = False,
    delete: bool = False,
    comments: bool = False,
    analytics: bool = False,
    mentions: bool = False,
    hashtags: bool = False,
    public_media: bool = False,
    max_caption: int | None = None,
    media_types: tuple[str, ...] = (),
    daily_limit: int | None = None,
) -> SocialProviderCapabilities:
    return SocialProviderCapabilities(
        supports_text=text,
        supports_single_image=image,
        supports_multiple_images=multiple_images,
        supports_video=video,
        supports_reels=False,
        supports_stories=False,
        supports_scheduling=scheduling,
        supports_delete=delete,
        max_text_length=max_caption or 0,
        supported_media_types=media_types,
        daily_publication_limit=daily_limit,
        supports_short_video=short_video,
        supports_comments=comments,
        supports_analytics=analytics,
        supports_mentions=mentions,
        supports_hashtags=hashtags,
        requires_public_media_url=public_media,
    )


NOT_IMPLEMENTED_CAPABILITIES = _capabilities()
FACEBOOK_CAPABILITIES = _capabilities(
    text=True,
    image=True,
    scheduling=True,
    hashtags=True,
    public_media=True,
    max_caption=63_206,
    media_types=("image/jpeg", "image/png"),
)
INSTAGRAM_CAPABILITIES = _capabilities(
    image=True,
    scheduling=True,
    hashtags=True,
    public_media=True,
    max_caption=2_200,
    media_types=("image/jpeg", "image/png"),
    daily_limit=100,
)


def build_provider_catalog(
    *,
    meta_enabled: bool = True,
    linkedin_enabled: bool = False,
    youtube_enabled: bool = False,
    tiktok_enabled: bool = False,
    reddit_enabled: bool = False,
) -> ProviderCatalog:
    planned = ProviderStatus.PLANNED
    definitions = (
        ProviderDefinition(
            provider="meta",
            display_name="Meta",
            status=ProviderStatus.VERIFIED_IN_DEVELOPMENT,
            enabled=meta_enabled,
            platforms=(
                PlatformDefinition(
                    "facebook",
                    "Facebook",
                    "Pages",
                    ProviderStatus.VERIFIED_IN_DEVELOPMENT,
                    True,
                    FACEBOOK_CAPABILITIES,
                    FACEBOOK_CAPABILITIES,
                ),
                PlatformDefinition(
                    "instagram",
                    "Instagram",
                    "Business or Creator accounts",
                    ProviderStatus.VERIFIED_IN_DEVELOPMENT,
                    True,
                    INSTAGRAM_CAPABILITIES,
                    INSTAGRAM_CAPABILITIES,
                ),
            ),
        ),
        ProviderDefinition(
            "linkedin",
            "LinkedIn",
            planned,
            linkedin_enabled,
            (
                PlatformDefinition(
                    "linkedin",
                    "LinkedIn",
                    "Professional profiles and organization pages",
                    planned,
                    False,
                    _capabilities(text=True, image=True, multiple_images=True, video=True),
                    NOT_IMPLEMENTED_CAPABILITIES,
                ),
            ),
        ),
        ProviderDefinition(
            "youtube",
            "YouTube",
            planned,
            youtube_enabled,
            (
                PlatformDefinition(
                    "youtube",
                    "YouTube",
                    "Videos and Shorts",
                    planned,
                    False,
                    _capabilities(video=True, short_video=True, delete=True, analytics=True),
                    NOT_IMPLEMENTED_CAPABILITIES,
                ),
            ),
        ),
        ProviderDefinition(
            "tiktok",
            "TikTok",
            planned,
            tiktok_enabled,
            (
                PlatformDefinition(
                    "tiktok",
                    "TikTok",
                    "Creator video and photo publishing",
                    planned,
                    False,
                    _capabilities(image=True, video=True, short_video=True),
                    NOT_IMPLEMENTED_CAPABILITIES,
                ),
            ),
        ),
        ProviderDefinition(
            "reddit",
            "Reddit",
            planned,
            reddit_enabled,
            (
                PlatformDefinition(
                    "reddit",
                    "Reddit",
                    "Community posts",
                    planned,
                    False,
                    _capabilities(text=True, image=True),
                    NOT_IMPLEMENTED_CAPABILITIES,
                ),
            ),
        ),
    )
    return ProviderCatalog(definitions)
