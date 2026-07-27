from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import JobQueue, SocialUnitOfWork
from socialos.application.social.use_cases import ApplicationNotFoundError, RetryPublication
from socialos.domain.social import Platform, Publication, PublicationStatus, Workspace


@pytest.mark.asyncio
async def test_retry_publication_requeues_retryable_failure() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.FAILED_RETRYABLE)
    publication.last_error = "Meta returned a temporary rate limit"
    publication.next_attempt_at = datetime(2026, 7, 27, 12, 0)
    uow = RetryPublicationUow(workspace, publication)
    queue = RecordingJobQueue()

    result = await RetryPublication(
        lambda: cast(SocialUnitOfWork, uow),
        cast(JobQueue, queue),
    ).execute(make_actor(), publication.id)

    assert result.status == PublicationStatus.QUEUED
    assert result.last_error is None
    assert result.next_attempt_at is not None
    assert queue.enqueued_publication_ids == [publication.id]
    assert uow.committed is True


@pytest.mark.asyncio
async def test_retry_publication_requeues_uncertain_publication() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.UNCERTAIN)
    uow = RetryPublicationUow(workspace, publication)
    queue = RecordingJobQueue()

    result = await RetryPublication(
        lambda: cast(SocialUnitOfWork, uow),
        cast(JobQueue, queue),
    ).execute(make_actor(), publication.id)

    assert result.status == PublicationStatus.QUEUED
    assert queue.enqueued_publication_ids == [publication.id]


@pytest.mark.asyncio
async def test_retry_publication_rejects_non_retryable_state() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.FAILED_PERMANENT)
    uow = RetryPublicationUow(workspace, publication)
    queue = RecordingJobQueue()

    with pytest.raises(ValueError, match="Only retryable or uncertain"):
        await RetryPublication(
            lambda: cast(SocialUnitOfWork, uow),
            cast(JobQueue, queue),
        ).execute(make_actor(), publication.id)

    assert publication.status == PublicationStatus.FAILED_PERMANENT
    assert queue.enqueued_publication_ids == []
    assert uow.committed is False


@pytest.mark.asyncio
async def test_retry_publication_hides_other_tenant_publication() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.FAILED_RETRYABLE)
    uow = RetryPublicationUow(workspace, publication)
    queue = RecordingJobQueue()

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await RetryPublication(
            lambda: cast(SocialUnitOfWork, uow),
            cast(JobQueue, queue),
        ).execute(
            Actor(user_id="user_2", organization_id="org_2", role=OrganizationRole.ADMIN),
            publication.id,
        )

    assert queue.enqueued_publication_ids == []


def make_workspace() -> Workspace:
    return Workspace(
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )


def make_actor() -> Actor:
    return Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN)


def make_publication(workspace_id: UUID, status: PublicationStatus) -> Publication:
    return Publication(
        workspace_id=workspace_id,
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Kinetic Mobiles now offers same-day diagnostics for business fleets.",
        status=status,
    )


class RetryPublicationUow:
    def __init__(self, workspace: Workspace, publication: Publication) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.publications = PublicationRepo(publication)
        self.committed = False

    async def __aenter__(self) -> "RetryPublicationUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class WorkspaceRepo:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get_by_external_organization_id(
        self, external_organization_id: str
    ) -> Workspace | None:
        if self._workspace.external_organization_id != external_organization_id:
            return None
        return self._workspace


class PublicationRepo:
    def __init__(self, publication: Publication) -> None:
        self._publication = publication

    async def get(self, publication_id: UUID, workspace_id: UUID) -> Publication | None:
        if self._publication.id != publication_id or self._publication.workspace_id != workspace_id:
            return None
        return self._publication

    async def update(self, publication: Publication) -> Publication:
        self._publication = publication
        return publication


class RecordingJobQueue:
    def __init__(self) -> None:
        self.enqueued_publication_ids: list[UUID] = []

    async def enqueue_publication(
        self,
        publication_id: UUID,
        run_at: datetime | None = None,
    ) -> None:
        self.enqueued_publication_ids.append(publication_id)
