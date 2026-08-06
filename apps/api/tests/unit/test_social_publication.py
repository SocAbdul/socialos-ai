from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialProvider, SocialUnitOfWork
from socialos.application.social.use_cases import (
    CreatePublication,
    CreatePublicationCommand,
    PublishQueuedPublication,
)
from socialos.domain.social import (
    AttemptStatus,
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


def test_publication_can_be_scheduled_from_ready_state() -> None:
    publication = Publication(
        workspace_id=uuid4(),
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.INSTAGRAM,
        caption="Launch day",
        status=PublicationStatus.READY,
    )

    run_at = datetime.now(UTC) + timedelta(hours=1)
    publication.schedule(run_at)

    assert publication.status == PublicationStatus.SCHEDULED
    assert publication.scheduled_at == run_at


@pytest.mark.asyncio
async def test_publish_job_is_idempotent_when_external_id_exists() -> None:
    publication = Publication(
        workspace_id=uuid4(),
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Already done",
        status=PublicationStatus.QUEUED,
        external_publication_id="external-1",
    )
    uow = InMemoryUow(publication=publication)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.PUBLISHED
    assert provider.publish_calls == 0


@pytest.mark.asyncio
async def test_publish_job_records_successful_attempt_once() -> None:
    connection = PlatformConnection(
        workspace_id=uuid4(),
        provider="meta",
        platform=Platform.FACEBOOK,
        external_account_id="page-1",
        external_account_name="Kinetic Mobiles",
        encrypted_credentials="encrypted",
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
        capabilities={"supports_text": True},
        last_validated_at=datetime.now(UTC),
    )
    publication = Publication(
        workspace_id=connection.workspace_id,
        content_item_id=uuid4(),
        platform_connection_id=connection.id,
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Test",
        status=PublicationStatus.QUEUED,
    )
    account = SocialAccount(
        workspace_id=connection.workspace_id,
        platform_connection_id=connection.id,
        platform=Platform.FACEBOOK,
        account_type=SocialAccountType.FACEBOOK_PAGE,
        external_account_id="page-1",
        display_name="Kinetic Mobiles",
        capabilities={"supports_text": True, "supports_single_image": True},
        last_validated_at=datetime.now(UTC),
        id=publication.social_account_id,
    )
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.PUBLISHED
    assert result.external_publication_id == "meta-post-1"
    assert provider.publish_calls == 1
    assert [attempt.status for attempt in uow.attempts] == [
        AttemptStatus.STARTED,
        AttemptStatus.SUCCEEDED,
    ]


@pytest.mark.asyncio
async def test_retry_after_terminal_attempt_uses_next_attempt_number() -> None:
    connection, account, publication = make_ready_facebook_publication()
    publication.status = PublicationStatus.FAILED_RETRYABLE
    existing_attempts = [
        PublicationAttempt(
            publication_id=publication.id,
            attempt_number=1,
            status=AttemptStatus.STARTED,
            provider="meta",
        ),
        PublicationAttempt(
            publication_id=publication.id,
            attempt_number=1,
            status=AttemptStatus.FAILED_RETRYABLE,
            provider="meta",
            error_code="rate_limit",
            error_message="Meta rate limit",
        ),
    ]
    uow = InMemoryUow(
        publication=publication,
        connection=connection,
        account=account,
        attempts=existing_attempts,
    )
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.PUBLISHED
    assert [attempt.attempt_number for attempt in uow.attempts] == [1, 1, 2, 2]


@pytest.mark.asyncio
async def test_worker_death_before_meta_call_is_protected_by_active_lease() -> None:
    publication = Publication(
        workspace_id=uuid4(),
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Lease active",
        status=PublicationStatus.PUBLISHING,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        execution_key="worker-that-died",
    )
    uow = InMemoryUow(publication=publication)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is publication
    assert provider.publish_calls == 0


@pytest.mark.asyncio
async def test_meta_timeout_after_processing_marks_publication_uncertain() -> None:
    connection, account, publication = make_ready_facebook_publication()
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = TimeoutProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.UNCERTAIN
    assert result.uncertain_since is not None
    assert result.execution_key is None
    assert result.lease_expires_at is None
    assert provider.publish_calls == 1


@pytest.mark.asyncio
async def test_non_retryable_provider_error_marks_publication_permanent() -> None:
    connection, account, publication = make_ready_facebook_publication()
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = PermanentFailureProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.FAILED_PERMANENT
    assert result.next_attempt_at is None
    assert [attempt.status for attempt in uow.attempts] == [
        AttemptStatus.STARTED,
        AttemptStatus.FAILED_PERMANENT,
    ]
    assert uow.attempts[-1].provider == "meta"
    assert uow.attempts[-1].error_code == "190"


@pytest.mark.asyncio
async def test_missing_media_asset_fails_permanently_without_text_fallback() -> None:
    connection, account, publication = make_ready_facebook_publication()
    publication.media_asset_id = uuid4()
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.FAILED_PERMANENT
    assert result.last_error == "Media asset not found"
    assert result.lease_expires_at is None
    assert result.execution_key is None
    assert provider.publish_calls == 0
    assert [attempt.status for attempt in uow.attempts] == [
        AttemptStatus.STARTED,
        AttemptStatus.FAILED_PERMANENT,
    ]


@pytest.mark.asyncio
async def test_missing_social_account_records_permanent_attempt() -> None:
    connection, _account, publication = make_ready_facebook_publication()
    uow = InMemoryUow(publication=publication, connection=connection, account=None)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.FAILED_PERMANENT
    assert result.last_error == "Social account not found"
    assert result.lease_expires_at is None
    assert result.execution_key is None
    assert provider.publish_calls == 0
    assert [attempt.status for attempt in uow.attempts] == [
        AttemptStatus.STARTED,
        AttemptStatus.FAILED_PERMANENT,
    ]


@pytest.mark.asyncio
async def test_existing_image_asset_uses_image_provider_path() -> None:
    connection, account, publication = make_ready_facebook_publication()
    media_asset = MediaAsset(
        workspace_id=publication.workspace_id,
        uploader_id="user_1",
        media_type=MediaType.IMAGE,
        storage_url="https://cdn.socialos.ai/workspaces/kinetic/image.jpg",
        content_type="image/jpeg",
        checksum_sha256="a" * 64,
    )
    publication.media_asset_id = media_asset.id
    uow = InMemoryUow(
        publication=publication,
        connection=connection,
        media_asset=media_asset,
        account=account,
    )
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is not None
    assert result.status == PublicationStatus.PUBLISHED
    assert provider.publish_calls == 1
    assert provider.publish_image_calls == 1
    assert provider.publish_text_calls == 0


@pytest.mark.asyncio
async def test_two_workers_receiving_same_job_do_not_duplicate_after_success() -> None:
    connection, account, publication = make_ready_facebook_publication()
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = FakeProvider()
    use_case = PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    )

    first = await use_case.execute(publication.id)
    second = await use_case.execute(publication.id)

    assert first is not None
    assert second is not None
    assert second.external_publication_id == "meta-post-1"
    assert provider.publish_calls == 1


@pytest.mark.asyncio
async def test_manual_and_automatic_retry_during_active_lease_do_not_duplicate() -> None:
    connection, account, publication = make_ready_facebook_publication()
    publication.status = PublicationStatus.PUBLISHING
    publication.lease_expires_at = datetime.now(UTC) + timedelta(minutes=5)
    publication.execution_key = "automatic-worker"
    uow = InMemoryUow(publication=publication, connection=connection, account=account)
    provider = FakeProvider()

    result = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"meta": cast(SocialProvider, provider)},
    ).execute(publication.id)

    assert result is publication
    assert provider.publish_calls == 0


@pytest.mark.asyncio
async def test_instagram_text_only_is_rejected_before_enqueue() -> None:
    connection = PlatformConnection(
        workspace_id=uuid4(),
        provider="meta",
        platform=Platform.INSTAGRAM,
        external_account_id="ig-1",
        external_account_name="Kinetic Mobiles",
        encrypted_credentials="encrypted",
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
        capabilities={"supports_text": False},
        last_validated_at=datetime.now(UTC),
    )
    account = SocialAccount(
        workspace_id=connection.workspace_id,
        platform_connection_id=connection.id,
        platform=Platform.INSTAGRAM,
        account_type=SocialAccountType.INSTAGRAM_BUSINESS,
        external_account_id="ig-1",
        display_name="Kinetic Mobiles",
        capabilities={"supports_text": False, "supports_single_image": True},
        last_validated_at=datetime.now(UTC),
    )
    uow = CreatePublicationUow(connection, account)
    actor = Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN)

    with pytest.raises(ValueError, match="text-only"):
        await CreatePublication(lambda: cast(SocialUnitOfWork, uow)).execute(
            actor,
            CreatePublicationCommand(
                workspace_id=connection.workspace_id,
                content_item_id=uuid4(),
                platform_connection_id=connection.id,
                social_account_id=account.id,
                platform=Platform.INSTAGRAM,
                caption="Text only",
                media_asset_id=None,
            ),
        )


def make_ready_facebook_publication() -> tuple[PlatformConnection, SocialAccount, Publication]:
    connection = PlatformConnection(
        workspace_id=uuid4(),
        provider="meta",
        platform=Platform.FACEBOOK,
        external_account_id="page-1",
        external_account_name="Kinetic Mobiles",
        encrypted_credentials="encrypted",
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
        capabilities={"supports_text": True},
        last_validated_at=datetime.now(UTC),
    )
    publication = Publication(
        workspace_id=connection.workspace_id,
        content_item_id=uuid4(),
        platform_connection_id=connection.id,
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Test",
        status=PublicationStatus.QUEUED,
    )
    account = SocialAccount(
        workspace_id=connection.workspace_id,
        platform_connection_id=connection.id,
        platform=Platform.FACEBOOK,
        account_type=SocialAccountType.FACEBOOK_PAGE,
        external_account_id="page-1",
        display_name="Kinetic Mobiles",
        capabilities={"supports_text": True, "supports_single_image": True},
        last_validated_at=datetime.now(UTC),
        id=publication.social_account_id,
    )
    return connection, account, publication


class InMemoryUow:
    def __init__(
        self,
        publication: Publication,
        connection: PlatformConnection | None = None,
        media_asset: MediaAsset | None = None,
        account: SocialAccount | None = None,
        attempts: list[PublicationAttempt] | None = None,
    ) -> None:
        self.publications = InMemoryPublicationRepo(publication)
        self.platform_connections = InMemoryConnectionRepo(connection)
        self.media_assets = InMemoryMediaRepo(media_asset)
        self.social_accounts = InMemorySocialAccountRepo(account)
        self.publication_attempts = InMemoryAttemptRepo(attempts)
        self.attempts = self.publication_attempts.items

    async def __aenter__(self) -> "InMemoryUow":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class InMemoryPublicationRepo:
    def __init__(self, publication: Publication) -> None:
        self.publication = publication

    async def get_for_update(self, publication_id: object) -> Publication | None:
        return self.publication if publication_id == self.publication.id else None

    async def update(self, publication: Publication) -> Publication:
        self.publication = publication
        return publication


class InMemoryConnectionRepo:
    def __init__(self, connection: PlatformConnection | None) -> None:
        self.connection = connection

    async def get(self, connection_id: object, workspace_id: object) -> PlatformConnection | None:
        if (
            self.connection
            and self.connection.id == connection_id
            and self.connection.workspace_id == workspace_id
        ):
            return self.connection
        return None


class InMemoryMediaRepo:
    def __init__(self, media_asset: MediaAsset | None) -> None:
        self.media_asset = media_asset

    async def get(self, media_asset_id: object, workspace_id: object) -> MediaAsset | None:
        if (
            self.media_asset
            and self.media_asset.id == media_asset_id
            and self.media_asset.workspace_id == workspace_id
        ):
            return self.media_asset
        return None


class InMemorySocialAccountRepo:
    def __init__(self, account: SocialAccount | None) -> None:
        self.account = account

    async def get(self, account_id: object, workspace_id: object) -> SocialAccount | None:
        if (
            self.account
            and self.account.id == account_id
            and self.account.workspace_id == workspace_id
        ):
            return self.account
        return None


class InMemoryAttemptRepo:
    def __init__(self, attempts: list[PublicationAttempt] | None = None) -> None:
        self.items: list[PublicationAttempt] = attempts or []

    async def add(self, attempt: PublicationAttempt) -> PublicationAttempt:
        self.items.append(attempt)
        return attempt

    async def count_for_publication(self, publication_id: object) -> int:
        return max(
            (
                item.attempt_number
                for item in self.items
                if getattr(item, "publication_id", None) == publication_id
            ),
            default=0,
        )


class FakeProvider:
    provider_name = "meta"

    def __init__(self) -> None:
        self.publish_calls = 0
        self.publish_text_calls = 0
        self.publish_image_calls = 0
        self.publish_video_calls = 0

    async def publish_text(self, *args: object, **kwargs: object) -> object:
        self.publish_calls += 1
        self.publish_text_calls += 1
        return FakeResult()

    async def publish_image(self, *args: object, **kwargs: object) -> object:
        self.publish_calls += 1
        self.publish_image_calls += 1
        return FakeResult()

    async def publish_video(self, *args: object, **kwargs: object) -> object:
        self.publish_calls += 1
        self.publish_video_calls += 1
        return FakeResult()


class TimeoutProvider(FakeProvider):
    async def publish_text(self, *args: object, **kwargs: object) -> object:
        self.publish_calls += 1
        raise TimeoutError("Meta timeout after processing request")


class PermanentProviderError(RuntimeError):
    retryable = False
    error_code = "190"


class PermanentFailureProvider(FakeProvider):
    async def publish_text(self, *args: object, **kwargs: object) -> object:
        self.publish_calls += 1
        raise PermanentProviderError("Invalid OAuth access token")


class FakeResult:
    external_publication_id = "meta-post-1"
    external_url = "https://www.facebook.com/meta-post-1"
    provider_request_id = "request-1"


class CreatePublicationUow:
    def __init__(self, connection: PlatformConnection, account: SocialAccount) -> None:
        self.workspaces = WorkspaceRepo(connection.workspace_id)
        self.platform_connections = InMemoryConnectionRepo(connection)
        self.social_accounts = InMemorySocialAccountRepo(account)
        self.publications = PublicationSink()

    async def __aenter__(self) -> "CreatePublicationUow":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class WorkspaceRepo:
    def __init__(self, workspace_id: UUID) -> None:
        self.workspace_id = workspace_id

    async def get(self, workspace_id: UUID) -> Workspace | None:
        if workspace_id != self.workspace_id:
            return None
        return Workspace(
            id=workspace_id,
            owner_id="user_1",
            external_organization_id="org_1",
            name="Kinetic Mobiles",
        )


class PublicationSink:
    async def add(self, publication: Publication) -> Publication:
        return publication
