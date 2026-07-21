from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol
from uuid import UUID

from socialos.domain.social import (
    AIGeneration,
    AIOperation,
    BrandProfile,
    Campaign,
    ContentItem,
    MediaAsset,
    Platform,
    PlatformConnection,
    Publication,
    PublicationAttempt,
    SocialAccount,
    SocialAccountType,
    Workspace,
)


@dataclass(frozen=True, slots=True)
class SocialProviderCapabilities:
    supports_text: bool
    supports_single_image: bool
    supports_multiple_images: bool
    supports_video: bool
    supports_reels: bool
    supports_stories: bool
    supports_scheduling: bool
    supports_delete: bool
    max_text_length: int
    supported_media_types: tuple[str, ...]
    daily_publication_limit: int | None

    def as_dict(self) -> dict[str, object]:
        return {
            "supports_text": self.supports_text,
            "supports_single_image": self.supports_single_image,
            "supports_multiple_images": self.supports_multiple_images,
            "supports_video": self.supports_video,
            "supports_reels": self.supports_reels,
            "supports_stories": self.supports_stories,
            "supports_scheduling": self.supports_scheduling,
            "supports_delete": self.supports_delete,
            "max_text_length": self.max_text_length,
            "supported_media_types": list(self.supported_media_types),
            "daily_publication_limit": self.daily_publication_limit,
        }


@dataclass(frozen=True, slots=True)
class OAuthConnectionCandidate:
    platform: Platform
    account_type: SocialAccountType
    external_account_id: str
    external_account_name: str
    username: str | None
    parent_external_account_id: str | None
    access_token: str
    expires_at: datetime | None
    scopes: list[str]
    capabilities: SocialProviderCapabilities
    safe_metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class PublishResult:
    external_publication_id: str
    external_url: str | None
    provider_request_id: str | None = None


class WorkspaceRepository(Protocol):
    async def add(self, workspace: Workspace) -> Workspace: ...

    async def get(self, workspace_id: UUID) -> Workspace | None: ...

    async def get_by_external_organization_id(
        self, external_organization_id: str
    ) -> Workspace | None: ...


class BrandProfileRepository(Protocol):
    async def add(self, brand_profile: BrandProfile) -> BrandProfile: ...

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[BrandProfile]: ...


class PlatformConnectionRepository(Protocol):
    async def add(self, connection: PlatformConnection) -> PlatformConnection: ...

    async def get(self, connection_id: UUID, workspace_id: UUID) -> PlatformConnection | None: ...

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[PlatformConnection]: ...


class SocialAccountRepository(Protocol):
    async def add(self, account: SocialAccount) -> SocialAccount: ...

    async def get(self, account_id: UUID, workspace_id: UUID) -> SocialAccount | None: ...

    async def list_for_connection(self, connection_id: UUID) -> Sequence[SocialAccount]: ...

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[SocialAccount]: ...


class CampaignRepository(Protocol):
    async def add(self, campaign: Campaign) -> Campaign: ...

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Campaign]: ...


class ContentItemRepository(Protocol):
    async def add(self, content_item: ContentItem) -> ContentItem: ...

    async def get(self, content_item_id: UUID, workspace_id: UUID) -> ContentItem | None: ...


class MediaAssetRepository(Protocol):
    async def add(self, media_asset: MediaAsset) -> MediaAsset: ...

    async def get(self, media_asset_id: UUID, workspace_id: UUID) -> MediaAsset | None: ...


class PublicationRepository(Protocol):
    async def add(self, publication: Publication) -> Publication: ...

    async def get(self, publication_id: UUID, workspace_id: UUID) -> Publication | None: ...

    async def get_for_update(self, publication_id: UUID) -> Publication | None: ...

    async def update(self, publication: Publication) -> Publication: ...

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Publication]: ...


class PublicationAttemptRepository(Protocol):
    async def add(self, attempt: PublicationAttempt) -> PublicationAttempt: ...

    async def list_for_publication(self, publication_id: UUID) -> Sequence[PublicationAttempt]: ...

    async def count_for_publication(self, publication_id: UUID) -> int: ...


class AIGenerationRepository(Protocol):
    async def add(self, generation: AIGeneration) -> AIGeneration: ...

    async def get_by_hash(
        self, workspace_id: UUID, operation: AIOperation, input_hash: str
    ) -> AIGeneration | None: ...


class SocialUnitOfWork(Protocol):
    workspaces: WorkspaceRepository
    brand_profiles: BrandProfileRepository
    platform_connections: PlatformConnectionRepository
    social_accounts: SocialAccountRepository
    campaigns: CampaignRepository
    content_items: ContentItemRepository
    media_assets: MediaAssetRepository
    publications: PublicationRepository
    publication_attempts: PublicationAttemptRepository
    ai_generations: AIGenerationRepository

    async def __aenter__(self) -> "SocialUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class SocialProvider(Protocol):
    provider_name: str

    def authorize(self, state: str, scopes: Sequence[str]) -> str: ...

    async def exchange_code(self, code: str) -> Sequence[OAuthConnectionCandidate]: ...

    async def refresh_credentials(self, encrypted_credentials: str) -> str: ...

    async def validate_connection(self, encrypted_credentials: str) -> bool: ...

    async def publish_text(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        *,
        idempotency_key: str,
    ) -> PublishResult: ...

    async def publish_image(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult: ...

    async def publish_video(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        caption: str,
        media_url: str,
        *,
        idempotency_key: str,
    ) -> PublishResult: ...

    async def get_publication_status(
        self,
        connection: PlatformConnection,
        account: SocialAccount,
        external_publication_id: str,
    ) -> str: ...

    async def delete_publication(
        self, connection: PlatformConnection, external_publication_id: str
    ) -> None: ...

    def get_capabilities(self, platform: Platform) -> SocialProviderCapabilities: ...


class TokenCipher(Protocol):
    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str: ...


class JobQueue(Protocol):
    async def enqueue_publication(
        self, publication_id: UUID, run_at: datetime | None = None
    ) -> None: ...


class AIContentService(Protocol):
    provider: str
    model: str
    prompt_version: str

    async def generate_caption(self, text: str) -> tuple[str, dict[str, int], str, int]: ...

    async def adapt_for_platform(
        self, text: str, platform: Platform
    ) -> tuple[str, dict[str, int], str, int]: ...

    async def generate_hashtags(self, text: str) -> tuple[str, dict[str, int], str, int]: ...

    async def generate_call_to_action(self, text: str) -> tuple[str, dict[str, int], str, int]: ...

    async def rewrite_tone(self, text: str, tone: str) -> tuple[str, dict[str, int], str, int]: ...

    async def translate_content(
        self, text: str, locale: str
    ) -> tuple[str, dict[str, int], str, int]: ...
