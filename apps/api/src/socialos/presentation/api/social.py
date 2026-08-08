from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

from socialos.application.common.auth import Actor
from socialos.application.social.use_cases import (
    AdaptContentForPlatform,
    ApplicationNotFoundError,
    CancelPublication,
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
    EnsureLocalDevelopmentSocialAccounts,
    GetPublicationDetail,
    ListBrandProfiles,
    ListCampaigns,
    ListContentItems,
    ListMediaAssets,
    ListPlatformConnections,
    ListPublications,
    ListSocialAccounts,
    LocalDevelopmentConnectionError,
    PublishPublicationNow,
    RegisterMediaAsset,
    RegisterMediaAssetCommand,
    RequestMediaUpload,
    RequestMediaUploadCommand,
    RetryPublication,
    SchedulePublication,
    UploadMedia,
    UploadMediaCommand,
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
    PublicationAttempt,
    SocialAccount,
    Workspace,
)
from socialos.infrastructure.ai.content_service import LocalAIContentService
from socialos.infrastructure.database.session import SqlAlchemyUnitOfWork, session_factory
from socialos.infrastructure.security.oauth_state import OAuthStateError, OAuthStateStore
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta import MetaSocialProvider
from socialos.infrastructure.social.meta.integration import (
    MetaIntegrationService,
    MetaSessionError,
    MetaValidationTemporaryError,
)
from socialos.infrastructure.social.meta.provider import (
    META_REQUIRED_SCOPES,
    MetaPermissionError,
)
from socialos.infrastructure.storage.media import HTTPMediaPreflightService, build_media_storage
from socialos.infrastructure.tasks.job_queue import CeleryJobQueue
from socialos.presentation.api.dependencies import get_actor

router = APIRouter(tags=["social"])

BrandName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
CampaignName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)
]
ProfileText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)
]
ContentText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000)
]


def _cipher() -> FernetTokenCipher:
    return FernetTokenCipher(get_settings().token_encryption_key)


def _meta_provider() -> MetaSocialProvider:
    return MetaSocialProvider(get_settings(), _cipher())


def _media_preflight() -> HTTPMediaPreflightService | None:
    settings = get_settings()
    return HTTPMediaPreflightService(settings) if settings.social_provider == "meta" else None


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

    name: BrandName
    voice: ProfileText
    audience: ProfileText


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


class BrandProfileListResponse(BaseModel):
    items: list[BrandProfileResponse]


class AuthorizationUrlResponse(BaseModel):
    url: str
    channel_nonce: str
    return_to: str


class MetaAuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_intent: Literal["facebook", "instagram", "combined", "reconnect"]
    connection_id: UUID | None = None
    return_to: str = "/integrations"


class MetaOAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class MetaOAuthCallbackResponse(BaseModel):
    session_id: str
    channel_nonce: str
    return_to: str


class MetaSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=20, max_length=200)


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


class LocalDevelopmentSocialAccountsResponse(BaseModel):
    connections: list[PlatformConnectionResponse]
    accounts: list[SocialAccountResponse]


class CreateCampaignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_profile_id: UUID
    name: CampaignName


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


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]


class CreateContentItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: UUID
    body: ContentText


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


class ContentItemListResponse(BaseModel):
    items: list[ContentItemResponse]


class RegisterMediaAssetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: MediaType
    storage_url: HttpUrl
    content_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
    ]
    checksum_sha256: str = Field(min_length=64, max_length=64)


class RequestMediaUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: MediaType
    content_type: str = Field(min_length=1, max_length=128)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(gt=0)


class MediaUploadTargetResponse(BaseModel):
    object_key: str
    upload_url: str
    public_url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime
    max_size_bytes: int


class MediaAssetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    media_type: MediaType
    storage_url: str
    content_type: str
    checksum_sha256: str
    storage_key: str
    size_bytes: int

    @classmethod
    def from_domain(cls, asset: MediaAsset) -> MediaAssetResponse:
        return cls(
            id=asset.id,
            workspace_id=asset.workspace_id,
            media_type=asset.media_type,
            storage_url=asset.storage_url,
            content_type=asset.content_type,
            checksum_sha256=asset.checksum_sha256,
            storage_key=asset.storage_key,
            size_bytes=asset.size_bytes,
        )


class MediaAssetListResponse(BaseModel):
    items: list[MediaAssetResponse]


class AdaptContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: ContentText
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
    caption: ContentText
    media_asset_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=16, max_length=96)


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
    media_asset_id: UUID | None
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
            media_asset_id=publication.media_asset_id,
            status=publication.status.value,
            scheduled_at=publication.scheduled_at,
            external_publication_id=publication.external_publication_id,
            external_url=publication.external_url,
            last_error=publication.last_error,
            next_attempt_at=publication.next_attempt_at,
        )


class PublicationListResponse(BaseModel):
    items: list[PublicationResponse]


class PublicationAttemptResponse(BaseModel):
    id: UUID
    publication_id: UUID
    attempt_number: int
    status: str
    provider: str
    request_id: str | None
    error_code: str | None
    error_message: str | None
    external_publication_id: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, attempt: PublicationAttempt) -> PublicationAttemptResponse:
        return cls(
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


class PublicationDetailResponse(PublicationResponse):
    attempts: list[PublicationAttemptResponse]


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


@router.get("/workspaces/{workspace_id}/brand-profiles")
async def list_brand_profiles(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> BrandProfileListResponse:
    brands = await ListBrandProfiles(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return BrandProfileListResponse(
        items=[BrandProfileResponse.from_domain(brand) for brand in brands]
    )


@router.get("/workspaces/{workspace_id}/integrations/meta")
async def meta_integration_status(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> dict[str, object]:
    async with session_factory() as session:
        try:
            return await MetaIntegrationService(session, _meta_provider(), _cipher()).status(
                actor=actor, workspace_id=workspace_id
            )
        except MetaSessionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workspaces/{workspace_id}/integrations/meta/authorize")
async def meta_authorize(
    workspace_id: UUID,
    request: MetaAuthorizeRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AuthorizationUrlResponse:
    try:
        async with session_factory() as session:
            service = MetaIntegrationService(session, _meta_provider(), _cipher())
            await service.ensure_workspace_access(actor=actor, workspace_id=workspace_id)
            if request.connection_intent == "reconnect":
                if request.connection_id is None:
                    raise OAuthStateError("Reconnect requires a connection_id")
                await service.ensure_connection_access(
                    actor=actor, connection_id=request.connection_id
                )
            elif request.connection_id is not None:
                raise OAuthStateError("connection_id is only valid for reconnect")
            creation = await OAuthStateStore(session).create(
                workspace_id=workspace_id,
                user_id=actor.user_id,
                provider="meta",
                redirect_uri=get_settings().meta_redirect_uri,
                connection_intent=request.connection_intent,
                return_to=request.return_to,
                target_connection_id=request.connection_id,
            )
            await session.commit()
        url = _meta_provider().authorize(creation.state, sorted(META_REQUIRED_SCOPES))
    except (OAuthStateError, MetaSessionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthorizationUrlResponse(
        url=url, channel_nonce=creation.channel_nonce, return_to=request.return_to
    )


@router.post(
    "/integrations/meta/callback",
)
async def meta_callback(
    request: MetaOAuthCallbackRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> MetaOAuthCallbackResponse:
    try:
        async with session_factory() as session:
            record = await OAuthStateStore(session).consume(
                state=request.state,
                user_id=actor.user_id,
                provider="meta",
                redirect_uri=get_settings().meta_redirect_uri,
            )
            await session.commit()
            session_id = await MetaIntegrationService(
                session, _meta_provider(), _cipher()
            ).create_session(actor=actor, state=record, code=request.code)
    except (ValueError, ConnectionAuthorizationError, OAuthStateError, MetaPermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MetaOAuthCallbackResponse(
        session_id=session_id,
        channel_nonce=record.channel_nonce,
        return_to=record.return_to,
    )


@router.get("/integrations/meta/sessions/{session_id}")
async def get_meta_session(
    session_id: str,
    actor: Annotated[Actor, Depends(get_actor)],
) -> dict[str, object]:
    async with session_factory() as session:
        try:
            item = await MetaIntegrationService(session, _meta_provider(), _cipher()).get_session(
                actor=actor, public_id=session_id
            )
        except MetaSessionError as exc:
            raise HTTPException(
                status_code=404, detail="Meta connection session was not found"
            ) from exc
        return {
            "session_id": session_id,
            "connection_intent": item.connection_intent,
            "channel_nonce": item.channel_nonce,
            "return_to": item.return_to,
            "target_connection_id": (
                str(item.target_connection_id) if item.target_connection_id else None
            ),
            "candidates": item.candidates,
            "expires_at": item.expires_at,
            "completed": item.completed_at is not None,
            "result": item.result if item.completed_at is not None else None,
        }


@router.post("/integrations/meta/sessions/{session_id}/select")
async def select_meta_session(
    session_id: str,
    request: MetaSelectionRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> dict[str, object]:
    async with session_factory() as session:
        try:
            return await MetaIntegrationService(session, _meta_provider(), _cipher()).select(
                actor=actor, public_id=session_id, candidate_id=request.candidate_id
            )
        except MetaSessionError as exc:
            raise HTTPException(
                status_code=404, detail="Meta connection session was not found"
            ) from exc


@router.post("/platform-connections/{connection_id}/disconnect", status_code=204)
async def disconnect_meta_connection(
    connection_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> None:
    async with session_factory() as session:
        try:
            await MetaIntegrationService(session, _meta_provider(), _cipher()).disconnect(
                actor=actor, connection_id=connection_id
            )
        except MetaSessionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/platform-connections/{connection_id}/validate")
async def validate_meta_connection(
    connection_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> dict[str, bool]:
    async with session_factory() as session:
        try:
            valid = await MetaIntegrationService(session, _meta_provider(), _cipher()).validate(
                actor=actor, connection_id=connection_id
            )
        except MetaSessionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except MetaValidationTemporaryError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"valid": valid}


@router.get("/platform-connections/{connection_id}/details")
async def meta_connection_details(
    connection_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> dict[str, object]:
    async with session_factory() as session:
        try:
            return await MetaIntegrationService(session, _meta_provider(), _cipher()).details(
                actor=actor, connection_id=connection_id
            )
        except MetaSessionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@router.post(
    "/workspaces/{workspace_id}/platform-connections/local-development",
    summary="Create idempotent local-only social accounts for development walkthroughs",
)
async def ensure_local_development_social_accounts(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> LocalDevelopmentSocialAccountsResponse:
    settings = get_settings()
    if settings.social_provider != "local-dev":
        raise HTTPException(status_code=403, detail="Local social accounts are disabled")
    try:
        result = await EnsureLocalDevelopmentSocialAccounts(
            SqlAlchemyUnitOfWork,
            _cipher(),
            environment=settings.environment,
            auth_mode=settings.auth_mode,
        ).execute(actor, workspace_id)
    except LocalDevelopmentConnectionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LocalDevelopmentSocialAccountsResponse(
        connections=[
            PlatformConnectionResponse.from_domain(connection) for connection in result.connections
        ],
        accounts=[SocialAccountResponse.from_domain(account) for account in result.accounts],
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


@router.get("/workspaces/{workspace_id}/campaigns")
async def list_campaigns(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> CampaignListResponse:
    campaigns = await ListCampaigns(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return CampaignListResponse(
        items=[CampaignResponse.from_domain(campaign) for campaign in campaigns]
    )


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


@router.get("/workspaces/{workspace_id}/content-items")
async def list_content_items(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> ContentItemListResponse:
    items = await ListContentItems(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return ContentItemListResponse(items=[ContentItemResponse.from_domain(item) for item in items])


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
    "/workspaces/{workspace_id}/media-assets/upload-target",
)
async def request_media_upload(
    workspace_id: UUID,
    request: RequestMediaUploadRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> MediaUploadTargetResponse:
    try:
        target = await RequestMediaUpload(
            SqlAlchemyUnitOfWork,
            build_media_storage(get_settings()),
        ).execute(
            actor,
            RequestMediaUploadCommand(
                workspace_id=workspace_id,
                media_type=request.media_type,
                content_type=request.content_type,
                checksum_sha256=request.checksum_sha256,
                size_bytes=request.size_bytes,
            ),
        )
    except ApplicationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MediaUploadTargetResponse(
        object_key=target.object_key,
        upload_url=target.upload_url,
        public_url=target.public_url,
        method=target.method,
        headers=target.headers,
        expires_at=target.expires_at,
        max_size_bytes=target.max_size_bytes,
    )


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
            storage_url=str(request.storage_url),
            content_type=request.content_type,
            checksum_sha256=request.checksum_sha256,
        ),
    )
    return MediaAssetResponse.from_domain(asset)


@router.get("/workspaces/{workspace_id}/media-assets")
async def list_media_assets(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> MediaAssetListResponse:
    assets = await ListMediaAssets(SqlAlchemyUnitOfWork).execute(actor, workspace_id)
    return MediaAssetListResponse(items=[MediaAssetResponse.from_domain(asset) for asset in assets])


@router.post(
    "/workspaces/{workspace_id}/media-assets/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_media_asset(
    workspace_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
    file: Annotated[UploadFile, File()],
) -> MediaAssetResponse:
    settings = get_settings()
    content = await file.read(settings.media_max_upload_bytes + 1)
    if len(content) > settings.media_max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image upload exceeds the 15 MB limit")
    try:
        asset = await UploadMedia(SqlAlchemyUnitOfWork, build_media_storage(settings)).execute(
            actor,
            UploadMediaCommand(
                workspace_id=workspace_id,
                filename=file.filename or "",
                content_type=file.content_type or "",
                content=content,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
                idempotency_key=request.idempotency_key,
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


@router.get(
    "/publications/{publication_id}",
    response_model=PublicationDetailResponse,
    summary="Get publication details and attempt history",
)
async def get_publication(
    publication_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationDetailResponse:
    detail = await GetPublicationDetail(SqlAlchemyUnitOfWork).execute(actor, publication_id)
    return PublicationDetailResponse(
        **PublicationResponse.from_domain(detail.publication).model_dump(),
        attempts=[PublicationAttemptResponse.from_domain(attempt) for attempt in detail.attempts],
    )


@router.post("/publications/{publication_id}/schedule")
async def schedule_publication(
    publication_id: UUID,
    request: SchedulePublicationRequest,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    publication = await SchedulePublication(
        SqlAlchemyUnitOfWork, CeleryJobQueue(), _media_preflight()
    ).execute(actor, publication_id, request.run_at)
    return PublicationResponse.from_domain(publication)


@router.post("/publications/{publication_id}/publish-now")
async def publish_now(
    publication_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    try:
        publication = await PublishPublicationNow(
            SqlAlchemyUnitOfWork, CeleryJobQueue(), _media_preflight()
        ).execute(actor, publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PublicationResponse.from_domain(publication)


@router.post("/publications/{publication_id}/retry")
async def retry_publication(
    publication_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    try:
        publication = await RetryPublication(
            SqlAlchemyUnitOfWork, CeleryJobQueue(), _media_preflight()
        ).execute(actor, publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PublicationResponse.from_domain(publication)


@router.post("/publications/{publication_id}/cancel")
async def cancel_publication(
    publication_id: UUID,
    actor: Annotated[Actor, Depends(get_actor)],
) -> PublicationResponse:
    try:
        publication = await CancelPublication(SqlAlchemyUnitOfWork).execute(actor, publication_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PublicationResponse.from_domain(publication)
