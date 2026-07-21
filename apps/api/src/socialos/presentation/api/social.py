from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from socialos.application.common.auth import Actor
from socialos.application.social.use_cases import (
    AdaptContentForPlatform,
    ApplicationNotFoundError,
    BuildMetaAuthorizationUrl,
    CompleteMetaOAuth,
    ConnectionAuthorizationError,
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
    ListPlatformConnections,
    ListPublications,
    ListSocialAccounts,
    PublishPublicationNow,
    RegisterMediaAsset,
    RegisterMediaAssetCommand,
    SchedulePublication,
)
from socialos.config import get_settings
from socialos.domain.social import (
    AIGeneration,
    BrandProfile,
    Campaign,
    ContentItem,
    MediaAsset,
    MediaType,
    Platform,
    PlatformConnection,
    Publication,
    SocialAccount,
    Workspace,
)
from socialos.infrastructure.ai.content_service import LocalAIContentService
from socialos.infrastructure.database.session import SqlAlchemyUnitOfWork, session_factory
from socialos.infrastructure.security.oauth_state import OAuthStateError, OAuthStateStore
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta import MetaSocialProvider
from socialos.infrastructure.tasks.job_queue import CeleryJobQueue
from socialos.presentation.api.dependencies import get_actor

router = APIRouter(tags=["social"])


def _cipher() -> FernetTokenCipher:
    return FernetTokenCipher(get_settings().token_encryption_key)


def _meta_provider() -> MetaSocialProvider:
    return MetaSocialProvider(get_settings(), _cipher())


@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: CreateWorkspaceRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> WorkspaceResponse:
    workspace = await CreateWorkspace(SqlAlchemyUnitOfWork).execute(
        actor, CreateWorkspaceCommand(name=request.name)
    )
    return WorkspaceResponse.from_domain(workspace)


@router.post(
    "/workspaces/{workspace_id}/brand-profiles",
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_profile(
    workspace_id: UUID,
    request: CreateBrandProfileRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> BrandProfileResponse:
    brand = await CreateBrandProfile(SqlAlchemyUnitOfWork).execute(
        actor,
        CreateBrandProfileCommand(
            workspace_id=workspace_id,
            name=request.name,
            voice=request.voice,
            audience=request.audience,
        ),
    )
    return BrandProfileResponse.from_domain(brand)


@router.get(
    "/workspaces/{workspace_id}/platform-connections/meta/authorize",
)
async def meta_authorize(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AuthorizationUrlResponse:
    async with session_factory() as session:
        state = await OAuthStateStore(session).create(
            workspace_id=workspace_id,
            user_id=actor.user_id,
            provider="meta",
            redirect_uri=get_settings().meta_redirect_uri,
        )
        await session.commit()
    url = await BuildMetaAuthorizationUrl(_meta_provider()).execute(actor, workspace_id, state)
    return AuthorizationUrlResponse(url=url)


@router.get(
    "/platform-connections/meta/callback",
)
async def meta_callback(
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
    actor: Annotated[Actor, Depends(get_actor)],
) -> PlatformConnectionListResponse:
    try:
        async with session_factory() as session:
            record = await OAuthStateStore(session).consume(
                state=state,
                user_id=actor.user_id,
                provider="meta",
                redirect_uri=get_settings().meta_redirect_uri,
            )
            await session.commit()
        workspace_id = record.workspace_id
        connections = await CompleteMetaOAuth(
            SqlAlchemyUnitOfWork,
            _meta_provider(),
            _cipher(),
        ).execute(actor, workspace_id, code)
    except (ValueError, ConnectionAuthorizationError, OAuthStateError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlatformConnectionListResponse(
        items=[PlatformConnectionResponse.from_domain(connection) for connection in connections]
    )


@router.get(
    "/workspaces/{workspace_id}/platform-connections",
)
async def list_platform_connections(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PlatformConnectionListResponse:
    connections = await ListPlatformConnections(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return PlatformConnectionListResponse(
        items=[PlatformConnectionResponse.from_domain(connection) for connection in connections]
    )


@router.get("/workspaces/{workspace_id}/social-accounts")
async def list_social_accounts(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> SocialAccountListResponse:
    accounts = await ListSocialAccounts(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return SocialAccountListResponse(
        items=[SocialAccountResponse.from_domain(account) for account in accounts]
    )


@router.post(
    "/workspaces/{workspace_id}/campaigns",
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    workspace_id: UUID,
    request: CreateCampaignRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> CampaignResponse:
    campaign = await CreateCampaign(SqlAlchemyUnitOfWork).execute(
        actor,
        CreateCampaignCommand(
            workspace_id=workspace_id,
            brand_profile_id=request.brand_profile_id,
            name=request.name,
        ),
    )
    return CampaignResponse.from_domain(campaign)


@router.post(
    "/workspaces/{workspace_id}/content-items",
    status_code=status.HTTP_201_CREATED,
)
async def create_content_item(
    workspace_id: UUID,
    request: CreateContentItemRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> ContentItemResponse:
    item = await CreateContentItem(SqlAlchemyUnitOfWork).execute(
        actor,
        CreateContentItemCommand(
            workspace_id=workspace_id,
            campaign_id=request.campaign_id,
            body=request.body,
        ),
    )
    return ContentItemResponse.from_domain(item)


@router.post(
    "/workspaces/{workspace_id}/ai/adapt-for-platform",
)
async def adapt_for_platform(
    workspace_id: UUID,
    request: AdaptContentRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AIGenerationResponse:
    generation = await AdaptContentForPlatform(
        SqlAlchemyUnitOfWork,
        LocalAIContentService(),
    ).execute(actor, workspace_id, request.text, request.platform)
    return AIGenerationResponse.from_domain(generation)


@router.post(
    "/workspaces/{workspace_id}/media-assets",
    status_code=status.HTTP_201_CREATED,
)
async def register_media_asset(
    workspace_id: UUID,
    request: RegisterMediaAssetRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> MediaAssetResponse:
    asset = await RegisterMediaAsset(SqlAlchemyUnitOfWork).execute(
        actor,
        RegisterMediaAssetCommand(
            workspace_id=workspace_id,
            media_type=request.media_type,
            storage_url=request.storage_url,
            content_type=request.content_type,
            checksum_sha256=request.checksum_sha256,
        ),
    )
    return MediaAssetResponse.from_domain(asset)


@router.post(
    "/workspaces/{workspace_id}/publications",
    status_code=status.HTTP_201_CREATED,
)
async def create_publication(
    workspace_id: UUID,
    request: CreatePublicationRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    try:
        publication = await CreatePublication(SqlAlchemyUnitOfWork).execute(
            actor,
            CreatePublicationCommand(
                workspace_id=workspace_id,
                content_item_id=request.content_item_id,
                platform_connection_id=request.platform_connection_id,
                social_account_id=request.social_account_id,
                platform=request.platform,
                caption=request.caption,
                media_asset_id=request.media_asset_id,
            ),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PublicationResponse.from_domain(publication)


@router.get("/workspaces/{workspace_id}/publications")
async def list_publications(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationListResponse:
    publications = await ListPublications(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return PublicationListResponse(
        items=[PublicationResponse.from_domain(publication) for publication in publications]
    )


@router.post("/publications/{publication_id}/schedule")
async def schedule_publication(
    publication_id: UUID,
    request: SchedulePublicationRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    publication = await SchedulePublication(SqlAlchemyUnitOfWork, CeleryJobQueue()).execute(
        actor, publication_id, request.run_at
    )
    return PublicationResponse.from_domain(publication)


@router.post("/publications/{publication_id}/publish-now")
async def publish_now(
    publication_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    publication = await PublishPublicationNow(SqlAlchemyUnitOfWork, CeleryJobQueue()).execute(
        actor, publication_id
    )
    return PublicationResponse.from_domain(publication)


class CreateWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    owner_id: str
    external_organization_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, workspace: Workspace) -> WorkspaceResponse:
        return cls(
            id=workspace.id,
            name=workspace.name,
            owner_id=workspace.owner_id,
            external_organization_id=workspace.external_organization_id,
            created_at=workspace.created_at,
        )


class CreateBrandProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    voice: str = Field(default="", max_length=5000)
    audience: str = Field(default="", max_length=5000)


class BrandProfileResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    voice: str
    audience: str

    @classmethod
    def from_domain(cls, brand: BrandProfile) -> BrandProfileResponse:
        return cls(
            id=brand.id,
            workspace_id=brand.workspace_id,
            name=brand.name,
            voice=brand.voice,
            audience=brand.audience,
        )


class AuthorizationUrlResponse(BaseModel):
    url: str


class PlatformConnectionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    provider: str
    platform: Platform
    external_account_id: str
    external_account_name: str
    capabilities: dict[str, object]
    is_valid: bool
    expires_at: datetime | None

    @classmethod
    def from_domain(cls, connection: PlatformConnection) -> PlatformConnectionResponse:
        return cls(
            id=connection.id,
            workspace_id=connection.workspace_id,
            provider=connection.provider,
            platform=connection.platform,
            external_account_id=connection.external_account_id,
            external_account_name=connection.external_account_name,
            capabilities=connection.capabilities,
            is_valid=connection.is_valid,
            expires_at=connection.expires_at,
        )


class PlatformConnectionListResponse(BaseModel):
    items: list[PlatformConnectionResponse]


class SocialAccountResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    platform_connection_id: UUID
    platform: Platform
    account_type: str
    external_account_id: str
    display_name: str
    username: str | None
    capabilities: dict[str, object]
    selected: bool
    active: bool
    last_validated_at: datetime | None

    @classmethod
    def from_domain(cls, account: SocialAccount) -> SocialAccountResponse:
        return cls(
            id=account.id,
            workspace_id=account.workspace_id,
            platform_connection_id=account.platform_connection_id,
            platform=account.platform,
            account_type=account.account_type.value,
            external_account_id=account.external_account_id,
            display_name=account.display_name,
            username=account.username,
            capabilities=account.capabilities,
            selected=account.selected,
            active=account.active,
            last_validated_at=account.last_validated_at,
        )


class SocialAccountListResponse(BaseModel):
    items: list[SocialAccountResponse]


class CreateCampaignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_profile_id: UUID
    name: str = Field(min_length=1, max_length=180)


class CampaignResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    brand_profile_id: UUID
    name: str

    @classmethod
    def from_domain(cls, campaign: Campaign) -> CampaignResponse:
        return cls(
            id=campaign.id,
            workspace_id=campaign.workspace_id,
            brand_profile_id=campaign.brand_profile_id,
            name=campaign.name,
        )


class CreateContentItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: UUID
    body: str = Field(min_length=1, max_length=10_000)


class ContentItemResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    campaign_id: UUID
    body: str

    @classmethod
    def from_domain(cls, item: ContentItem) -> ContentItemResponse:
        return cls(
            id=item.id, workspace_id=item.workspace_id, campaign_id=item.campaign_id, body=item.body
        )


class RegisterMediaAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: MediaType
    storage_url: str
    content_type: str
    checksum_sha256: str = Field(min_length=64, max_length=64)


class MediaAssetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    media_type: MediaType
    storage_url: str
    content_type: str

    @classmethod
    def from_domain(cls, asset: MediaAsset) -> MediaAssetResponse:
        return cls(
            id=asset.id,
            workspace_id=asset.workspace_id,
            media_type=asset.media_type,
            storage_url=asset.storage_url,
            content_type=asset.content_type,
        )


class AdaptContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10_000)
    platform: Platform


class AIGenerationResponse(BaseModel):
    id: UUID
    operation: str
    provider: str
    model: str
    prompt_version: str
    input_hash: str
    token_usage: dict[str, int]
    estimated_cost: str
    latency_ms: int
    result: str
    created_at: datetime

    @classmethod
    def from_domain(cls, generation: AIGeneration) -> AIGenerationResponse:
        return cls(
            id=generation.id,
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


class CreatePublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_item_id: UUID
    platform_connection_id: UUID
    social_account_id: UUID
    platform: Platform
    caption: str = Field(min_length=1, max_length=10_000)
    media_asset_id: UUID | None = None


class SchedulePublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_at: datetime


class PublicationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    content_item_id: UUID
    platform_connection_id: UUID
    social_account_id: UUID
    platform: Platform
    caption: str
    status: str
    scheduled_at: datetime | None
    external_publication_id: str | None
    external_url: str | None
    last_error: str | None
    next_attempt_at: datetime | None

    @classmethod
    def from_domain(cls, publication: Publication) -> PublicationResponse:
        return cls(
            id=publication.id,
            workspace_id=publication.workspace_id,
            content_item_id=publication.content_item_id,
            platform_connection_id=publication.platform_connection_id,
            social_account_id=publication.social_account_id,
            platform=publication.platform,
            caption=publication.caption,
            status=publication.status.value,
            scheduled_at=publication.scheduled_at,
            external_publication_id=publication.external_publication_id,
            external_url=publication.external_url,
            last_error=publication.last_error,
            next_attempt_at=publication.next_attempt_at,
        )


class PublicationListResponse(BaseModel):
    items: list[PublicationResponse]
