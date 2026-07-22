import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from socialos.application.common.auth import Actor, Permission
from socialos.application.social.ports import (
    AIContentService,
    JobQueue,
    SocialProvider,
    SocialUnitOfWork,
    TokenCipher,
)
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
    Workspace,
)


class ApplicationNotFoundError(LookupError):
    """Raised when a requested tenant-scoped resource does not exist."""


class ConnectionAuthorizationError(PermissionError):
    """Raised when a platform connection cannot be authorized or validated."""


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    name: str


class CreateWorkspace:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreateWorkspaceCommand) -> Workspace:
        actor.require(Permission.ORGANIZATION_MANAGE)
        async with self._uow_factory() as uow:
            existing = await uow.workspaces.get_by_external_organization_id(actor.organization_id)
            if existing:
                return existing
            workspace = Workspace(
                owner_id=actor.user_id,
                external_organization_id=actor.organization_id,
                name=command.name,
            )
            await uow.workspaces.add(workspace)
            await uow.commit()
            return workspace


async def require_workspace(uow: SocialUnitOfWork, actor: Actor, workspace_id: UUID) -> Workspace:
    workspace = await uow.workspaces.get(workspace_id)
    if workspace is None:
        raise ApplicationNotFoundError("Workspace not found")
    if (
        workspace.external_organization_id != actor.organization_id
        and workspace.owner_id != actor.user_id
    ):
        raise ApplicationNotFoundError("Workspace not found")
    return workspace


@dataclass(frozen=True, slots=True)
class CreateBrandProfileCommand:
    workspace_id: UUID
    name: str
    voice: str = ""
    audience: str = ""


class CreateBrandProfile:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreateBrandProfileCommand) -> BrandProfile:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, command.workspace_id)
            brand = BrandProfile(
                workspace_id=command.workspace_id,
                name=command.name,
                voice=command.voice,
                audience=command.audience,
            )
            await uow.brand_profiles.add(brand)
            await uow.commit()
            return brand


class ListPlatformConnections:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, workspace_id: UUID) -> list[PlatformConnection]:
        actor.require(Permission.POSTS_READ)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, workspace_id)
            return list(await uow.platform_connections.list_for_workspace(workspace_id))


class ListSocialAccounts:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, workspace_id: UUID) -> list[SocialAccount]:
        actor.require(Permission.POSTS_READ)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, workspace_id)
            return list(await uow.social_accounts.list_for_workspace(workspace_id))


class BuildMetaAuthorizationUrl:
    def __init__(self, provider: SocialProvider) -> None:
        self._provider = provider

    async def execute(self, actor: Actor, workspace_id: UUID, state: str) -> str:
        actor.require(Permission.ORGANIZATION_MANAGE)
        scopes = [
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
            "instagram_basic",
            "instagram_content_publish",
        ]
        return self._provider.authorize(state, scopes)


class CompleteMetaOAuth:
    def __init__(
        self,
        uow_factory: Callable[[], SocialUnitOfWork],
        provider: SocialProvider,
        cipher: TokenCipher,
    ) -> None:
        self._uow_factory = uow_factory
        self._provider = provider
        self._cipher = cipher

    async def execute(
        self, actor: Actor, workspace_id: UUID, code: str
    ) -> list[PlatformConnection]:
        actor.require(Permission.ORGANIZATION_MANAGE)
        candidates = await self._provider.exchange_code(code)
        if not candidates:
            raise ConnectionAuthorizationError("Meta did not return compatible accounts")
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, workspace_id)
            connections: list[PlatformConnection] = []
            for candidate in candidates:
                encrypted_credentials = self._cipher.encrypt(
                    json.dumps({"access_token": candidate.access_token})
                )
                connection = PlatformConnection(
                    workspace_id=workspace_id,
                    provider=self._provider.provider_name,
                    platform=candidate.platform,
                    external_account_id=candidate.external_account_id,
                    external_account_name=candidate.external_account_name,
                    encrypted_credentials=encrypted_credentials,
                    scopes=candidate.scopes,
                    granted_scopes=candidate.scopes,
                    capabilities=candidate.capabilities.as_dict(),
                    expires_at=candidate.expires_at,
                )
                await uow.platform_connections.add(connection)
                await uow.social_accounts.add(
                    SocialAccount(
                        workspace_id=workspace_id,
                        platform_connection_id=connection.id,
                        platform=candidate.platform,
                        account_type=candidate.account_type,
                        external_account_id=candidate.external_account_id,
                        display_name=candidate.external_account_name,
                        username=candidate.username,
                        capabilities=candidate.capabilities.as_dict(),
                        selected=True,
                        safe_metadata={
                            "parent_external_account_id": candidate.parent_external_account_id
                        },
                    )
                )
                connections.append(connection)
            await uow.commit()
            return connections


@dataclass(frozen=True, slots=True)
class CreateCampaignCommand:
    workspace_id: UUID
    brand_profile_id: UUID
    name: str


class CreateCampaign:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreateCampaignCommand) -> Campaign:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, command.workspace_id)
            campaign = Campaign(
                workspace_id=command.workspace_id,
                brand_profile_id=command.brand_profile_id,
                name=command.name,
            )
            await uow.campaigns.add(campaign)
            await uow.commit()
            return campaign


@dataclass(frozen=True, slots=True)
class CreateContentItemCommand:
    workspace_id: UUID
    campaign_id: UUID
    body: str


class CreateContentItem:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreateContentItemCommand) -> ContentItem:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, command.workspace_id)
            item = ContentItem(
                workspace_id=command.workspace_id,
                campaign_id=command.campaign_id,
                author_id=actor.user_id,
                body=command.body,
            )
            await uow.content_items.add(item)
            await uow.commit()
            return item


@dataclass(frozen=True, slots=True)
class RegisterMediaAssetCommand:
    workspace_id: UUID
    media_type: MediaType
    storage_url: str
    content_type: str
    checksum_sha256: str


class RegisterMediaAsset:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: RegisterMediaAssetCommand) -> MediaAsset:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, command.workspace_id)
            asset = MediaAsset(
                workspace_id=command.workspace_id,
                uploader_id=actor.user_id,
                media_type=command.media_type,
                storage_url=command.storage_url,
                content_type=command.content_type,
                checksum_sha256=command.checksum_sha256,
            )
            await uow.media_assets.add(asset)
            await uow.commit()
            return asset


class AdaptContentForPlatform:
    def __init__(
        self,
        uow_factory: Callable[[], SocialUnitOfWork],
        ai_service: AIContentService,
    ) -> None:
        self._uow_factory = uow_factory
        self._ai_service = ai_service

    async def execute(
        self, actor: Actor, workspace_id: UUID, text: str, platform: Platform
    ) -> AIGeneration:
        actor.require(Permission.POSTS_WRITE)
        operation = AIOperation.ADAPT_FOR_PLATFORM
        input_hash = _input_hash(operation, {"text": text, "platform": platform.value})
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, workspace_id)
            cached = await uow.ai_generations.get_by_hash(workspace_id, operation, input_hash)
            if cached:
                return cached
            (
                result,
                token_usage,
                estimated_cost,
                latency_ms,
            ) = await self._ai_service.adapt_for_platform(text, platform)
            generation = AIGeneration(
                workspace_id=workspace_id,
                operation=operation,
                provider=self._ai_service.provider,
                model=self._ai_service.model,
                prompt_version=self._ai_service.prompt_version,
                input_hash=input_hash,
                token_usage=token_usage,
                estimated_cost=estimated_cost,
                latency_ms=latency_ms,
                result=result,
            )
            await uow.ai_generations.add(generation)
            await uow.commit()
            return generation


@dataclass(frozen=True, slots=True)
class CreatePublicationCommand:
    workspace_id: UUID
    content_item_id: UUID
    platform_connection_id: UUID
    social_account_id: UUID
    platform: Platform
    caption: str
    media_asset_id: UUID | None = None


class CreatePublication:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, command: CreatePublicationCommand) -> Publication:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, command.workspace_id)
            connection = await uow.platform_connections.get(
                command.platform_connection_id, command.workspace_id
            )
            if connection is None:
                raise ApplicationNotFoundError("Platform connection not found")
            account = await uow.social_accounts.get(command.social_account_id, command.workspace_id)
            if account is None or account.platform_connection_id != connection.id:
                raise ApplicationNotFoundError("Social account not found")
            _validate_publication_capabilities(account, command.caption, command.media_asset_id)
            publication = Publication(
                workspace_id=command.workspace_id,
                content_item_id=command.content_item_id,
                platform_connection_id=command.platform_connection_id,
                social_account_id=command.social_account_id,
                platform=command.platform,
                caption=command.caption,
                media_asset_id=command.media_asset_id,
                status=PublicationStatus.READY,
            )
            await uow.publications.add(publication)
            await uow.commit()
            return publication


class ListPublications:
    def __init__(self, uow_factory: Callable[[], SocialUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, actor: Actor, workspace_id: UUID) -> list[Publication]:
        actor.require(Permission.POSTS_READ)
        async with self._uow_factory() as uow:
            await require_workspace(uow, actor, workspace_id)
            return list(await uow.publications.list_for_workspace(workspace_id))


class SchedulePublication:
    def __init__(
        self,
        uow_factory: Callable[[], SocialUnitOfWork],
        job_queue: JobQueue,
    ) -> None:
        self._uow_factory = uow_factory
        self._job_queue = job_queue

    async def execute(self, actor: Actor, publication_id: UUID, run_at: datetime) -> Publication:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            workspace = await uow.workspaces.get_by_external_organization_id(actor.organization_id)
            if workspace is None:
                raise ApplicationNotFoundError("Workspace not found")
            publication = await uow.publications.get(publication_id, workspace.id)
            if publication is None:
                raise ApplicationNotFoundError("Publication not found")
            publication.schedule(run_at)
            await uow.publications.update(publication)
            await uow.commit()
        await self._job_queue.enqueue_publication(publication.id, run_at)
        return publication


class PublishPublicationNow:
    def __init__(
        self,
        uow_factory: Callable[[], SocialUnitOfWork],
        job_queue: JobQueue,
    ) -> None:
        self._uow_factory = uow_factory
        self._job_queue = job_queue

    async def execute(self, actor: Actor, publication_id: UUID) -> Publication:
        actor.require(Permission.POSTS_WRITE)
        async with self._uow_factory() as uow:
            workspace = await uow.workspaces.get_by_external_organization_id(actor.organization_id)
            if workspace is None:
                raise ApplicationNotFoundError("Workspace not found")
            publication = await uow.publications.get(publication_id, workspace.id)
            if publication is None:
                raise ApplicationNotFoundError("Publication not found")
            if publication.status in {PublicationStatus.PUBLISHED, PublicationStatus.PUBLISHING}:
                return publication
            publication.status = PublicationStatus.QUEUED
            publication.next_attempt_at = datetime.now(UTC)
            publication.updated_at = datetime.now(UTC)
            await uow.publications.update(publication)
            await uow.commit()
        await self._job_queue.enqueue_publication(publication.id)
        return publication


class PublishQueuedPublication:
    def __init__(
        self,
        uow_factory: Callable[[], SocialUnitOfWork],
        providers: dict[str, SocialProvider],
        max_attempts: int = 5,
    ) -> None:
        self._uow_factory = uow_factory
        self._providers = providers
        self._max_attempts = max_attempts

    async def execute(self, publication_id: UUID) -> Publication | None:
        execution_key = secrets.token_urlsafe(24)
        lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        attempt_number = 0
        async with self._uow_factory() as uow:
            publication = await uow.publications.get_for_update(publication_id)
            if publication is None:
                return None
            if publication.status in {
                PublicationStatus.PUBLISHED,
                PublicationStatus.FAILED_PERMANENT,
                PublicationStatus.CANCELLED,
            }:
                return publication
            if publication.external_publication_id:
                publication.status = PublicationStatus.PUBLISHED
                publication.updated_at = datetime.now(UTC)
                await uow.publications.update(publication)
                await uow.commit()
                return publication
            now = datetime.now(UTC)
            if (
                publication.status == PublicationStatus.PUBLISHING
                and publication.lease_expires_at is not None
                and publication.lease_expires_at > now
            ):
                return publication
            connection = await uow.platform_connections.get(
                publication.platform_connection_id, publication.workspace_id
            )
            if connection is None:
                publication.status = PublicationStatus.FAILED_PERMANENT
                publication.last_error = "Platform connection not found"
                await uow.publications.update(publication)
                await uow.commit()
                return publication
            provider = self._providers[connection.provider]
            attempt_number = (
                await uow.publication_attempts.count_for_publication(publication.id) + 1
            )
            publication.status = PublicationStatus.PUBLISHING
            publication.publishing_started_at = now
            publication.lease_expires_at = lease_expires_at
            publication.execution_key = execution_key
            publication.updated_at = now
            await uow.publications.update(publication)
            await uow.publication_attempts.add(
                PublicationAttempt(
                    publication_id=publication.id,
                    attempt_number=attempt_number,
                    status=AttemptStatus.STARTED,
                    provider=provider.provider_name,
                )
            )
            await uow.commit()

        try:
            media_asset: MediaAsset | None = None
            async with self._uow_factory() as uow:
                publication = await uow.publications.get_for_update(publication_id)
                if publication is None or publication.external_publication_id:
                    return publication
                if publication.execution_key != execution_key:
                    return publication
                connection = await uow.platform_connections.get(
                    publication.platform_connection_id, publication.workspace_id
                )
                if connection is None:
                    return publication
                account = await uow.social_accounts.get(
                    publication.social_account_id, publication.workspace_id
                )
                if account is None:
                    publication.status = PublicationStatus.FAILED_PERMANENT
                    publication.last_error = "Social account not found"
                    await uow.publications.update(publication)
                    await uow.commit()
                    return publication
                if publication.media_asset_id:
                    media_asset = await uow.media_assets.get(
                        publication.media_asset_id, publication.workspace_id
                    )
                provider = self._providers[connection.provider]
                if media_asset is None:
                    result = await provider.publish_text(
                        connection,
                        account,
                        publication.caption,
                        idempotency_key=publication.idempotency_key,
                    )
                elif media_asset.media_type == MediaType.IMAGE:
                    result = await provider.publish_image(
                        connection,
                        account,
                        publication.caption,
                        media_asset.storage_url,
                        idempotency_key=publication.idempotency_key,
                    )
                else:
                    result = await provider.publish_video(
                        connection,
                        account,
                        publication.caption,
                        media_asset.storage_url,
                        idempotency_key=publication.idempotency_key,
                    )
                publication.external_publication_id = result.external_publication_id
                publication.external_url = result.external_url
                publication.status = PublicationStatus.PUBLISHED
                publication.last_error = None
                publication.lease_expires_at = None
                publication.execution_key = None
                publication.uncertain_since = None
                publication.updated_at = datetime.now(UTC)
                await uow.publications.update(publication)
                await uow.publication_attempts.add(
                    PublicationAttempt(
                        publication_id=publication.id,
                        attempt_number=attempt_number,
                        status=AttemptStatus.SUCCEEDED,
                        provider=provider.provider_name,
                        request_id=result.provider_request_id,
                        external_publication_id=result.external_publication_id,
                    )
                )
                await uow.commit()
                return publication
        except Exception as exc:
            async with self._uow_factory() as uow:
                publication = await uow.publications.get_for_update(publication_id)
                if publication is None:
                    return None
                if publication.execution_key != execution_key:
                    return publication
                retryable = attempt_number < self._max_attempts
                uncertain = _is_uncertain_error(exc)
                if uncertain:
                    publication.status = PublicationStatus.UNCERTAIN
                    publication.uncertain_since = datetime.now(UTC)
                else:
                    publication.status = (
                        PublicationStatus.FAILED_RETRYABLE
                        if retryable
                        else PublicationStatus.FAILED_PERMANENT
                    )
                publication.last_error = str(exc)
                publication.next_attempt_at = (
                    datetime.now(UTC) + _backoff(attempt_number) if retryable else None
                )
                publication.lease_expires_at = None
                publication.execution_key = None
                publication.updated_at = datetime.now(UTC)
                await uow.publications.update(publication)
                await uow.publication_attempts.add(
                    PublicationAttempt(
                        publication_id=publication.id,
                        attempt_number=attempt_number,
                        status=(
                            AttemptStatus.UNCERTAIN
                            if uncertain
                            else (
                                AttemptStatus.FAILED_RETRYABLE
                                if retryable
                                else AttemptStatus.FAILED_PERMANENT
                            )
                        ),
                        provider="unknown",
                        error_message=str(exc),
                    )
                )
                await uow.commit()
                return publication


def _input_hash(operation: AIOperation, payload: dict[str, object]) -> str:
    canonical = json.dumps(
        {"operation": operation.value, "payload": payload}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _backoff(attempt_number: int) -> timedelta:
    seconds = min(900, 2 ** min(attempt_number, 8) * 30)
    return timedelta(seconds=seconds)


def _validate_publication_capabilities(
    account: SocialAccount, caption: str, media_asset_id: UUID | None
) -> None:
    raw_max_text_length = account.capabilities.get("max_text_length", 10_000)
    max_text_length = (
        int(raw_max_text_length) if isinstance(raw_max_text_length, int | str) else 10_000
    )
    if len(caption) > max_text_length:
        raise ValueError("Caption exceeds account capability limit")
    if media_asset_id is None and not bool(account.capabilities.get("supports_text")):
        raise ValueError("Selected social account does not support text-only publishing")
    if media_asset_id is not None and not bool(account.capabilities.get("supports_single_image")):
        raise ValueError("Selected social account does not support single-image publishing")


def _is_uncertain_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    return "timeout" in name or "timeout" in message or "connection" in message
