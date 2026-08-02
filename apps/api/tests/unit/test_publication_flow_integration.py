from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import (
    AdaptContentForPlatform,
    CancelPublication,
    CreateBrandProfile,
    CreateBrandProfileCommand,
    CreateCampaign,
    CreateCampaignCommand,
    CreateContentItem,
    CreateContentItemCommand,
    CreatePublication,
    CreatePublicationCommand,
    CreateWorkspace,
    CreateWorkspaceCommand,
    GetPublicationDetail,
    ListBrandProfiles,
    ListCampaigns,
    ListContentItems,
    ListMediaAssets,
    ListPublications,
    RegisterMediaAsset,
    RegisterMediaAssetCommand,
    RetryPublication,
    SchedulePublication,
)
from socialos.domain.social import (
    AIGeneration,
    AIOperation,
    BrandProfile,
    Campaign,
    ContentItem,
    MediaAsset,
    MediaType,
    Platform,
    PlatformConnection,
    Publication,
    PublicationAttempt,
    PublicationStatus,
    SocialAccount,
    SocialAccountType,
    Workspace,
)


@pytest.mark.asyncio
async def test_publication_management_flow_supports_status_retry_and_cancel() -> None:
    actor = Actor(
        user_id="user_kinetic_founder", organization_id="org_kinetic", role=OrganizationRole.ADMIN
    )
    uow = FlowUow()
    queue = RecordingQueue()

    workspace = await CreateWorkspace(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        CreateWorkspaceCommand(name="Kinetic Mobiles"),
    )
    connection, account = uow.seed_meta_account(workspace.id)

    brand = await CreateBrandProfile(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        CreateBrandProfileCommand(
            workspace_id=workspace.id,
            name="Kinetic Mobiles",
            voice="Helpful, local, confident, never gimmicky",
            audience="People who need fast phone repairs and trusted refurbished devices",
        ),
    )
    campaign = await CreateCampaign(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        CreateCampaignCommand(
            workspace_id=workspace.id,
            brand_profile_id=brand.id,
            name="Same-day screen repair launch",
        ),
    )
    content = await CreateContentItem(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        CreateContentItemCommand(
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            body="Kinetic Mobiles now offers same-day screen repairs with quality parts.",
        ),
    )
    media = await RegisterMediaAsset(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        RegisterMediaAssetCommand(
            workspace_id=workspace.id,
            media_type=MediaType.IMAGE,
            storage_url="https://cdn.socialos.local/kinetic/same-day-screen-repair.jpg",
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
        ),
    )
    generation = await AdaptContentForPlatform(
        lambda: cast(SocialUnitOfWork, uow),
        KineticAIContentService(),
    ).execute(actor, workspace.id, content.body, Platform.INSTAGRAM)
    publication = await CreatePublication(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        CreatePublicationCommand(
            workspace_id=workspace.id,
            content_item_id=content.id,
            platform_connection_id=connection.id,
            social_account_id=account.id,
            platform=Platform.INSTAGRAM,
            caption=generation.result,
            media_asset_id=media.id,
        ),
    )

    run_at = datetime.now(UTC) + timedelta(hours=2)
    scheduled = await SchedulePublication(
        lambda: cast(SocialUnitOfWork, uow),
        queue,
    ).execute(actor, publication.id, run_at)

    assert scheduled.status == PublicationStatus.SCHEDULED
    assert queue.enqueued == [(publication.id, run_at)]
    assert await ListBrandProfiles(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, workspace.id
    ) == [brand]
    assert await ListCampaigns(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, workspace.id
    ) == [campaign]
    assert await ListContentItems(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, workspace.id
    ) == [content]
    assert await ListMediaAssets(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, workspace.id
    ) == [media]
    assert await ListPublications(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, workspace.id
    ) == [publication]

    detail = await GetPublicationDetail(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor, publication.id
    )
    assert detail.publication.status == PublicationStatus.SCHEDULED
    assert detail.attempts == []

    publication.status = PublicationStatus.FAILED_RETRYABLE
    publication.last_error = "Meta rate limit: retry later"
    publication.next_attempt_at = datetime.now(UTC) + timedelta(minutes=5)

    retried = await RetryPublication(lambda: cast(SocialUnitOfWork, uow), queue).execute(
        actor,
        publication.id,
    )
    assert retried.status == PublicationStatus.QUEUED
    assert retried.last_error is None
    assert queue.enqueued[-1] == (publication.id, None)

    cancelled = await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor,
        publication.id,
    )
    assert cancelled.status == PublicationStatus.CANCELLED
    assert cancelled.next_attempt_at is None


class KineticAIContentService:
    provider = "local"
    model = "kinetic-test-adapter"
    prompt_version = "test-v1"

    async def generate_caption(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return text, {"input": 0, "output": 0}, "0.000000", 1

    async def adapt_for_platform(
        self,
        text: str,
        platform: Platform,
    ) -> tuple[str, dict[str, int], str, int]:
        return (
            f"{text} Book your repair slot today. #KineticMobiles #{platform.value.title()}",
            {"input": 12, "output": 16},
            "0.000000",
            2,
        )

    async def generate_hashtags(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return "#KineticMobiles", {"input": 0, "output": 0}, "0.000000", 1

    async def generate_call_to_action(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return "Book today", {"input": 0, "output": 0}, "0.000000", 1

    async def rewrite_tone(self, text: str, tone: str) -> tuple[str, dict[str, int], str, int]:
        return text, {"input": 0, "output": 0}, "0.000000", 1

    async def translate_content(
        self, text: str, locale: str
    ) -> tuple[str, dict[str, int], str, int]:
        return text, {"input": 0, "output": 0}, "0.000000", 1


class RecordingQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[UUID, datetime | None]] = []

    async def enqueue_publication(
        self,
        publication_id: UUID,
        run_at: datetime | None = None,
    ) -> None:
        self.enqueued.append((publication_id, run_at))


class FlowUow:
    def __init__(self) -> None:
        self.workspaces = WorkspaceRepo()
        self.brand_profiles = BrandProfileRepo()
        self.platform_connections = PlatformConnectionRepo()
        self.social_accounts = SocialAccountRepo()
        self.campaigns = CampaignRepo()
        self.content_items = ContentItemRepo()
        self.media_assets = MediaAssetRepo()
        self.publications = PublicationRepo()
        self.publication_attempts = PublicationAttemptRepo()
        self.ai_generations = AIGenerationRepo()

    async def __aenter__(self) -> "FlowUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    def seed_meta_account(self, workspace_id: UUID) -> tuple[PlatformConnection, SocialAccount]:
        capabilities: dict[str, object] = {
            "supports_text": True,
            "supports_single_image": True,
            "supports_video": False,
            "max_text_length": 2200,
        }
        connection = PlatformConnection(
            workspace_id=workspace_id,
            provider="meta",
            platform=Platform.INSTAGRAM,
            external_account_id="17841400000000000",
            external_account_name="Kinetic Mobiles",
            encrypted_credentials="encrypted-test-token",
            scopes=[
                "business_management",
                "pages_show_list",
                "pages_read_engagement",
                "pages_manage_posts",
                "instagram_basic",
                "instagram_content_publish",
            ],
            granted_scopes=[
                "business_management",
                "pages_show_list",
                "pages_read_engagement",
                "pages_manage_posts",
                "instagram_basic",
                "instagram_content_publish",
            ],
            capabilities=capabilities,
            last_validated_at=datetime.now(UTC),
        )
        account = SocialAccount(
            workspace_id=workspace_id,
            platform_connection_id=connection.id,
            platform=Platform.INSTAGRAM,
            account_type=SocialAccountType.INSTAGRAM_BUSINESS,
            external_account_id=connection.external_account_id,
            display_name="Kinetic Mobiles",
            username="kineticmobiles",
            capabilities=capabilities,
            selected=True,
            last_validated_at=datetime.now(UTC),
        )
        self.platform_connections.items.append(connection)
        self.social_accounts.items.append(account)
        return connection, account


class WorkspaceRepo:
    def __init__(self) -> None:
        self.items: list[Workspace] = []

    async def add(self, workspace: Workspace) -> Workspace:
        self.items.append(workspace)
        return workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        return next((item for item in self.items if item.id == workspace_id), None)

    async def get_by_external_organization_id(
        self,
        external_organization_id: str,
    ) -> Workspace | None:
        return next(
            (
                item
                for item in self.items
                if item.external_organization_id == external_organization_id
            ),
            None,
        )


class BrandProfileRepo:
    def __init__(self) -> None:
        self.items: list[BrandProfile] = []

    async def add(self, brand_profile: BrandProfile) -> BrandProfile:
        self.items.append(brand_profile)
        return brand_profile

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[BrandProfile]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class PlatformConnectionRepo:
    def __init__(self) -> None:
        self.items: list[PlatformConnection] = []

    async def add(self, connection: PlatformConnection) -> PlatformConnection:
        self.items.append(connection)
        return connection

    async def get(self, connection_id: UUID, workspace_id: UUID) -> PlatformConnection | None:
        return next(
            (
                item
                for item in self.items
                if item.id == connection_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[PlatformConnection]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class SocialAccountRepo:
    def __init__(self) -> None:
        self.items: list[SocialAccount] = []

    async def add(self, account: SocialAccount) -> SocialAccount:
        self.items.append(account)
        return account

    async def get(self, account_id: UUID, workspace_id: UUID) -> SocialAccount | None:
        return next(
            (
                item
                for item in self.items
                if item.id == account_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_connection(self, connection_id: UUID) -> Sequence[SocialAccount]:
        return [item for item in self.items if item.platform_connection_id == connection_id]

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[SocialAccount]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class CampaignRepo:
    def __init__(self) -> None:
        self.items: list[Campaign] = []

    async def add(self, campaign: Campaign) -> Campaign:
        self.items.append(campaign)
        return campaign

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Campaign]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class ContentItemRepo:
    def __init__(self) -> None:
        self.items: list[ContentItem] = []

    async def add(self, content_item: ContentItem) -> ContentItem:
        self.items.append(content_item)
        return content_item

    async def get(self, content_item_id: UUID, workspace_id: UUID) -> ContentItem | None:
        return next(
            (
                item
                for item in self.items
                if item.id == content_item_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[ContentItem]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class MediaAssetRepo:
    def __init__(self) -> None:
        self.items: list[MediaAsset] = []

    async def add(self, media_asset: MediaAsset) -> MediaAsset:
        self.items.append(media_asset)
        return media_asset

    async def get(self, media_asset_id: UUID, workspace_id: UUID) -> MediaAsset | None:
        return next(
            (
                item
                for item in self.items
                if item.id == media_asset_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[MediaAsset]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class PublicationRepo:
    def __init__(self) -> None:
        self.items: list[Publication] = []

    async def add(self, publication: Publication) -> Publication:
        self.items.append(publication)
        return publication

    async def get(self, publication_id: UUID, workspace_id: UUID) -> Publication | None:
        return next(
            (
                item
                for item in self.items
                if item.id == publication_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def get_for_update(self, publication_id: UUID) -> Publication | None:
        return next((item for item in self.items if item.id == publication_id), None)

    async def update(self, publication: Publication) -> Publication:
        return publication

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Publication]:
        return [item for item in self.items if item.workspace_id == workspace_id]


class PublicationAttemptRepo:
    def __init__(self) -> None:
        self.items: list[PublicationAttempt] = []

    async def add(self, attempt: PublicationAttempt) -> PublicationAttempt:
        self.items.append(attempt)
        return attempt

    async def list_for_publication(self, publication_id: UUID) -> Sequence[PublicationAttempt]:
        return [item for item in self.items if item.publication_id == publication_id]

    async def count_for_publication(self, publication_id: UUID) -> int:
        return len([item for item in self.items if item.publication_id == publication_id])


class AIGenerationRepo:
    def __init__(self) -> None:
        self.items: list[AIGeneration] = []

    async def add(self, generation: AIGeneration) -> AIGeneration:
        self.items.append(generation)
        return generation

    async def get_by_hash(
        self,
        workspace_id: UUID,
        operation: AIOperation,
        input_hash: str,
    ) -> AIGeneration | None:
        return next(
            (
                item
                for item in self.items
                if item.workspace_id == workspace_id
                and item.operation == operation
                and item.input_hash == input_hash
            ),
            None,
        )
