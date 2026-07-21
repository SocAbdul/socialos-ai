from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from socialos.application.posts.ports import PostRepository
from socialos.application.social.ports import (
    AIGenerationRepository,
    BrandProfileRepository,
    CampaignRepository,
    ContentItemRepository,
    MediaAssetRepository,
    PlatformConnectionRepository,
    PublicationAttemptRepository,
    PublicationRepository,
    SocialAccountRepository,
    WorkspaceRepository,
)
from socialos.domain.posts.entities import PostStatus, SocialPost
from socialos.domain.social import (
    AIGeneration,
    AIOperation,
    AttemptStatus,
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
from socialos.infrastructure.database.models import (
    AIGenerationModel,
    BrandProfileModel,
    CampaignModel,
    ContentItemModel,
    MediaAssetModel,
    PlatformConnectionModel,
    PostModel,
    PublicationAttemptModel,
    PublicationModel,
    SocialAccountModel,
    WorkspaceModel,
)


class SqlAlchemyPostRepository(PostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, post: SocialPost) -> SocialPost:
        self._session.add(
            PostModel(
                id=post.id,
                organization_id=post.organization_id,
                author_id=post.author_id,
                content=post.content,
                status=post.status.value,
                scheduled_at=post.scheduled_at,
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
        )
        return post

    async def list_for_organization(
        self, organization_id: str, *, limit: int, offset: int
    ) -> Sequence[SocialPost]:
        query: Select[tuple[PostModel]] = (
            select(PostModel)
            .where(PostModel.organization_id == organization_id)
            .order_by(PostModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = (await self._session.scalars(query)).all()
        return [self._to_domain(model) for model in models]

    @staticmethod
    def _to_domain(model: PostModel) -> SocialPost:
        post = object.__new__(SocialPost)
        post.organization_id = model.organization_id
        post.author_id = model.author_id
        post.content = model.content
        post.id = model.id
        post.status = PostStatus(model.status)
        post.scheduled_at = model.scheduled_at
        post.created_at = model.created_at
        post.updated_at = model.updated_at
        return post


class SqlAlchemyWorkspaceRepository(WorkspaceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> Workspace:
        self._session.add(
            WorkspaceModel(
                id=workspace.id,
                owner_id=workspace.owner_id,
                external_organization_id=workspace.external_organization_id,
                name=workspace.name,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
            )
        )
        return workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        model = await self._session.get(WorkspaceModel, workspace_id)
        return self._workspace(model) if model else None

    async def get_by_external_organization_id(
        self, external_organization_id: str
    ) -> Workspace | None:
        model = await self._session.scalar(
            select(WorkspaceModel).where(
                WorkspaceModel.external_organization_id == external_organization_id
            )
        )
        return self._workspace(model) if model else None

    @staticmethod
    def _workspace(model: WorkspaceModel) -> Workspace:
        workspace = object.__new__(Workspace)
        workspace.id = model.id
        workspace.owner_id = model.owner_id
        workspace.external_organization_id = model.external_organization_id
        workspace.name = model.name
        workspace.created_at = model.created_at
        workspace.updated_at = model.updated_at
        return workspace


class SqlAlchemyBrandProfileRepository(BrandProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, brand_profile: BrandProfile) -> BrandProfile:
        self._session.add(
            BrandProfileModel(
                id=brand_profile.id,
                workspace_id=brand_profile.workspace_id,
                name=brand_profile.name,
                voice=brand_profile.voice,
                audience=brand_profile.audience,
                created_at=brand_profile.created_at,
                updated_at=brand_profile.updated_at,
            )
        )
        return brand_profile

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[BrandProfile]:
        models = (
            await self._session.scalars(
                select(BrandProfileModel)
                .where(BrandProfileModel.workspace_id == workspace_id)
                .order_by(BrandProfileModel.created_at.desc())
            )
        ).all()
        return [self._brand(model) for model in models]

    @staticmethod
    def _brand(model: BrandProfileModel) -> BrandProfile:
        brand = object.__new__(BrandProfile)
        brand.id = model.id
        brand.workspace_id = model.workspace_id
        brand.name = model.name
        brand.voice = model.voice
        brand.audience = model.audience
        brand.created_at = model.created_at
        brand.updated_at = model.updated_at
        return brand


class SqlAlchemyPlatformConnectionRepository(PlatformConnectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, connection: PlatformConnection) -> PlatformConnection:
        self._session.add(
            PlatformConnectionModel(
                id=connection.id,
                workspace_id=connection.workspace_id,
                provider=connection.provider,
                platform=connection.platform.value,
                external_account_id=connection.external_account_id,
                external_account_name=connection.external_account_name,
                encrypted_credentials=connection.encrypted_credentials,
                scopes=connection.scopes,
                granted_scopes=connection.granted_scopes,
                capabilities=connection.capabilities,
                expires_at=connection.expires_at,
                reauth_required=connection.reauth_required,
                last_validated_at=connection.last_validated_at,
                revoked_at=connection.revoked_at,
                is_valid=connection.is_valid,
                created_at=connection.created_at,
                updated_at=connection.updated_at,
            )
        )
        return connection

    async def get(self, connection_id: UUID, workspace_id: UUID) -> PlatformConnection | None:
        model = await self._session.get(PlatformConnectionModel, connection_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        return self._connection(model)

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[PlatformConnection]:
        models = (
            await self._session.scalars(
                select(PlatformConnectionModel)
                .where(PlatformConnectionModel.workspace_id == workspace_id)
                .order_by(PlatformConnectionModel.created_at.desc())
            )
        ).all()
        return [self._connection(model) for model in models]

    @staticmethod
    def _connection(model: PlatformConnectionModel) -> PlatformConnection:
        connection = object.__new__(PlatformConnection)
        connection.id = model.id
        connection.workspace_id = model.workspace_id
        connection.provider = model.provider
        connection.platform = Platform(model.platform)
        connection.external_account_id = model.external_account_id
        connection.external_account_name = model.external_account_name
        connection.encrypted_credentials = model.encrypted_credentials
        connection.scopes = model.scopes
        connection.granted_scopes = model.granted_scopes
        connection.capabilities = model.capabilities
        connection.expires_at = model.expires_at
        connection.reauth_required = model.reauth_required
        connection.last_validated_at = model.last_validated_at
        connection.revoked_at = model.revoked_at
        connection.is_valid = model.is_valid
        connection.created_at = model.created_at
        connection.updated_at = model.updated_at
        return connection


class SqlAlchemySocialAccountRepository(SocialAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: SocialAccount) -> SocialAccount:
        self._session.add(
            SocialAccountModel(
                id=account.id,
                workspace_id=account.workspace_id,
                platform_connection_id=account.platform_connection_id,
                parent_account_id=account.parent_account_id,
                platform=account.platform.value,
                account_type=account.account_type.value,
                external_account_id=account.external_account_id,
                display_name=account.display_name,
                username=account.username,
                capabilities=account.capabilities,
                selected=account.selected,
                active=account.active,
                safe_metadata=account.safe_metadata,
                last_validated_at=account.last_validated_at,
                created_at=account.created_at,
                updated_at=account.updated_at,
            )
        )
        return account

    async def get(self, account_id: UUID, workspace_id: UUID) -> SocialAccount | None:
        model = await self._session.get(SocialAccountModel, account_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        return self._account(model)

    async def list_for_connection(self, connection_id: UUID) -> Sequence[SocialAccount]:
        models = (
            await self._session.scalars(
                select(SocialAccountModel).where(
                    SocialAccountModel.platform_connection_id == connection_id
                )
            )
        ).all()
        return [self._account(model) for model in models]

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[SocialAccount]:
        models = (
            await self._session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.workspace_id == workspace_id)
                .order_by(SocialAccountModel.created_at.desc())
            )
        ).all()
        return [self._account(model) for model in models]

    @staticmethod
    def _account(model: SocialAccountModel) -> SocialAccount:
        account = object.__new__(SocialAccount)
        account.id = model.id
        account.workspace_id = model.workspace_id
        account.platform_connection_id = model.platform_connection_id
        account.parent_account_id = model.parent_account_id
        account.platform = Platform(model.platform)
        account.account_type = SocialAccountType(model.account_type)
        account.external_account_id = model.external_account_id
        account.display_name = model.display_name
        account.username = model.username
        account.capabilities = model.capabilities
        account.selected = model.selected
        account.active = model.active
        account.safe_metadata = model.safe_metadata
        account.last_validated_at = model.last_validated_at
        account.created_at = model.created_at
        account.updated_at = model.updated_at
        return account


class SqlAlchemyCampaignRepository(CampaignRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, campaign: Campaign) -> Campaign:
        self._session.add(
            CampaignModel(
                id=campaign.id,
                workspace_id=campaign.workspace_id,
                brand_profile_id=campaign.brand_profile_id,
                name=campaign.name,
                created_at=campaign.created_at,
                updated_at=campaign.updated_at,
            )
        )
        return campaign

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Campaign]:
        models = (
            await self._session.scalars(
                select(CampaignModel)
                .where(CampaignModel.workspace_id == workspace_id)
                .order_by(CampaignModel.created_at.desc())
            )
        ).all()
        return [self._campaign(model) for model in models]

    @staticmethod
    def _campaign(model: CampaignModel) -> Campaign:
        campaign = object.__new__(Campaign)
        campaign.id = model.id
        campaign.workspace_id = model.workspace_id
        campaign.brand_profile_id = model.brand_profile_id
        campaign.name = model.name
        campaign.created_at = model.created_at
        campaign.updated_at = model.updated_at
        return campaign


class SqlAlchemyContentItemRepository(ContentItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, content_item: ContentItem) -> ContentItem:
        self._session.add(
            ContentItemModel(
                id=content_item.id,
                workspace_id=content_item.workspace_id,
                campaign_id=content_item.campaign_id,
                author_id=content_item.author_id,
                body=content_item.body,
                created_at=content_item.created_at,
                updated_at=content_item.updated_at,
            )
        )
        return content_item

    async def get(self, content_item_id: UUID, workspace_id: UUID) -> ContentItem | None:
        model = await self._session.get(ContentItemModel, content_item_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        item = object.__new__(ContentItem)
        item.id = model.id
        item.workspace_id = model.workspace_id
        item.campaign_id = model.campaign_id
        item.author_id = model.author_id
        item.body = model.body
        item.created_at = model.created_at
        item.updated_at = model.updated_at
        return item


class SqlAlchemyMediaAssetRepository(MediaAssetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, media_asset: MediaAsset) -> MediaAsset:
        self._session.add(
            MediaAssetModel(
                id=media_asset.id,
                workspace_id=media_asset.workspace_id,
                uploader_id=media_asset.uploader_id,
                media_type=media_asset.media_type.value,
                storage_url=media_asset.storage_url,
                content_type=media_asset.content_type,
                checksum_sha256=media_asset.checksum_sha256,
                created_at=media_asset.created_at,
            )
        )
        return media_asset

    async def get(self, media_asset_id: UUID, workspace_id: UUID) -> MediaAsset | None:
        model = await self._session.get(MediaAssetModel, media_asset_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        asset = object.__new__(MediaAsset)
        asset.id = model.id
        asset.workspace_id = model.workspace_id
        asset.uploader_id = model.uploader_id
        asset.media_type = MediaType(model.media_type)
        asset.storage_url = model.storage_url
        asset.content_type = model.content_type
        asset.checksum_sha256 = model.checksum_sha256
        asset.created_at = model.created_at
        return asset


class SqlAlchemyPublicationRepository(PublicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, publication: Publication) -> Publication:
        self._session.add(self._model(publication))
        return publication

    async def get(self, publication_id: UUID, workspace_id: UUID) -> Publication | None:
        model = await self._session.get(PublicationModel, publication_id)
        if model is None or model.workspace_id != workspace_id:
            return None
        return self._publication(model)

    async def get_for_update(self, publication_id: UUID) -> Publication | None:
        model = await self._session.scalar(
            select(PublicationModel).where(PublicationModel.id == publication_id).with_for_update()
        )
        return self._publication(model) if model else None

    async def update(self, publication: Publication) -> Publication:
        model = await self._session.get(PublicationModel, publication.id)
        if model is None:
            raise ValueError("Publication not found")
        model.status = publication.status.value
        model.caption = publication.caption
        model.scheduled_at = publication.scheduled_at
        model.external_publication_id = publication.external_publication_id
        model.external_url = publication.external_url
        model.container_id = publication.container_id
        model.container_status = publication.container_status
        model.last_error = publication.last_error
        model.next_attempt_at = publication.next_attempt_at
        model.publishing_started_at = publication.publishing_started_at
        model.lease_expires_at = publication.lease_expires_at
        model.execution_key = publication.execution_key
        model.uncertain_since = publication.uncertain_since
        model.updated_at = publication.updated_at
        return publication

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[Publication]:
        models = (
            await self._session.scalars(
                select(PublicationModel)
                .where(PublicationModel.workspace_id == workspace_id)
                .order_by(PublicationModel.created_at.desc())
            )
        ).all()
        return [self._publication(model) for model in models]

    @staticmethod
    def _model(publication: Publication) -> PublicationModel:
        return PublicationModel(
            id=publication.id,
            workspace_id=publication.workspace_id,
            content_item_id=publication.content_item_id,
            platform_connection_id=publication.platform_connection_id,
            social_account_id=publication.social_account_id,
            media_asset_id=publication.media_asset_id,
            platform=publication.platform.value,
            caption=publication.caption,
            scheduled_at=publication.scheduled_at,
            status=publication.status.value,
            idempotency_key=publication.idempotency_key,
            external_publication_id=publication.external_publication_id,
            external_url=publication.external_url,
            container_id=publication.container_id,
            container_status=publication.container_status,
            last_error=publication.last_error,
            next_attempt_at=publication.next_attempt_at,
            publishing_started_at=publication.publishing_started_at,
            lease_expires_at=publication.lease_expires_at,
            execution_key=publication.execution_key,
            uncertain_since=publication.uncertain_since,
            created_at=publication.created_at,
            updated_at=publication.updated_at,
        )

    @staticmethod
    def _publication(model: PublicationModel) -> Publication:
        publication = object.__new__(Publication)
        publication.id = model.id
        publication.workspace_id = model.workspace_id
        publication.content_item_id = model.content_item_id
        publication.platform_connection_id = model.platform_connection_id
        publication.social_account_id = model.social_account_id
        publication.media_asset_id = model.media_asset_id
        publication.platform = Platform(model.platform)
        publication.caption = model.caption
        publication.scheduled_at = model.scheduled_at
        publication.status = PublicationStatus(model.status)
        publication.idempotency_key = model.idempotency_key
        publication.external_publication_id = model.external_publication_id
        publication.external_url = model.external_url
        publication.container_id = model.container_id
        publication.container_status = model.container_status
        publication.last_error = model.last_error
        publication.next_attempt_at = model.next_attempt_at
        publication.publishing_started_at = model.publishing_started_at
        publication.lease_expires_at = model.lease_expires_at
        publication.execution_key = model.execution_key
        publication.uncertain_since = model.uncertain_since
        publication.created_at = model.created_at
        publication.updated_at = model.updated_at
        return publication


class SqlAlchemyPublicationAttemptRepository(PublicationAttemptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attempt: PublicationAttempt) -> PublicationAttempt:
        self._session.add(
            PublicationAttemptModel(
                id=attempt.id,
                publication_id=attempt.publication_id,
                attempt_number=attempt.attempt_number,
                status=attempt.status.value,
                provider=attempt.provider,
                request_id=attempt.request_id,
                error_code=attempt.error_code,
                error_message=attempt.error_message,
                external_publication_id=attempt.external_publication_id,
                created_at=attempt.created_at,
            )
        )
        return attempt

    async def list_for_publication(self, publication_id: UUID) -> Sequence[PublicationAttempt]:
        models = (
            await self._session.scalars(
                select(PublicationAttemptModel)
                .where(PublicationAttemptModel.publication_id == publication_id)
                .order_by(PublicationAttemptModel.created_at.desc())
            )
        ).all()
        return [self._attempt(model) for model in models]

    async def count_for_publication(self, publication_id: UUID) -> int:
        return len(await self.list_for_publication(publication_id))

    @staticmethod
    def _attempt(model: PublicationAttemptModel) -> PublicationAttempt:
        attempt = object.__new__(PublicationAttempt)
        attempt.id = model.id
        attempt.publication_id = model.publication_id
        attempt.attempt_number = model.attempt_number
        attempt.status = AttemptStatus(model.status)
        attempt.provider = model.provider
        attempt.request_id = model.request_id
        attempt.error_code = model.error_code
        attempt.error_message = model.error_message
        attempt.external_publication_id = model.external_publication_id
        attempt.created_at = model.created_at
        return attempt


class SqlAlchemyAIGenerationRepository(AIGenerationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, generation: AIGeneration) -> AIGeneration:
        self._session.add(
            AIGenerationModel(
                id=generation.id,
                workspace_id=generation.workspace_id,
                operation=generation.operation.value,
                provider=generation.provider,
                model=generation.model,
                prompt_version=generation.prompt_version,
                input_hash=generation.input_hash,
                token_usage=generation.token_usage,
                estimated_cost=generation.estimated_cost,
                latency_ms=generation.latency_ms,
                result=generation.result,
                created_at=generation.created_at,
            )
        )
        return generation

    async def get_by_hash(
        self, workspace_id: UUID, operation: AIOperation, input_hash: str
    ) -> AIGeneration | None:
        model = await self._session.scalar(
            select(AIGenerationModel).where(
                AIGenerationModel.workspace_id == workspace_id,
                AIGenerationModel.operation == operation.value,
                AIGenerationModel.input_hash == input_hash,
            )
        )
        if model is None:
            return None
        generation = object.__new__(AIGeneration)
        generation.id = model.id
        generation.workspace_id = model.workspace_id
        generation.operation = AIOperation(model.operation)
        generation.provider = model.provider
        generation.model = model.model
        generation.prompt_version = model.prompt_version
        generation.input_hash = model.input_hash
        generation.token_usage = model.token_usage
        generation.estimated_cost = model.estimated_cost
        generation.latency_ms = model.latency_ms
        generation.result = model.result
        generation.created_at = model.created_at
        return generation
