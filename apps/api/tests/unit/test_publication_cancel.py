from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import ApplicationNotFoundError, CancelPublication
from socialos.domain.social import Platform, Publication, PublicationStatus, Workspace


@pytest.mark.asyncio
async def test_cancel_publication_cancels_scheduled_publication() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.SCHEDULED)
    publication.scheduled_at = datetime.now(UTC) + timedelta(hours=2)
    publication.next_attempt_at = publication.scheduled_at
    uow = CancelPublicationUow(workspace, publication)

    result = await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), publication.id
    )

    assert result.status == PublicationStatus.CANCELLED
    assert result.next_attempt_at is None
    assert result.last_error is None
    assert uow.committed is True


@pytest.mark.asyncio
async def test_cancel_publication_cancels_queued_publication_before_worker_runs() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.QUEUED)
    publication.next_attempt_at = datetime.now(UTC)
    uow = CancelPublicationUow(workspace, publication)

    result = await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), publication.id
    )

    assert result.status == PublicationStatus.CANCELLED
    assert result.next_attempt_at is None
    assert uow.committed is True


@pytest.mark.asyncio
async def test_cancel_publication_is_idempotent_when_already_cancelled() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.CANCELLED)
    uow = CancelPublicationUow(workspace, publication)

    result = await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), publication.id
    )

    assert result.status == PublicationStatus.CANCELLED
    assert uow.committed is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        PublicationStatus.PUBLISHING,
        PublicationStatus.PUBLISHED,
        PublicationStatus.FAILED_PERMANENT,
    ],
)
async def test_cancel_publication_rejects_non_cancellable_states(
    status: PublicationStatus,
) -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, status)
    uow = CancelPublicationUow(workspace, publication)

    with pytest.raises(ValueError, match="cannot be cancelled"):
        await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
            make_actor(), publication.id
        )

    assert publication.status == status
    assert uow.committed is False


@pytest.mark.asyncio
async def test_cancel_publication_hides_other_tenant_publication() -> None:
    workspace = make_workspace()
    publication = make_publication(workspace.id, PublicationStatus.SCHEDULED)
    uow = CancelPublicationUow(workspace, publication)

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await CancelPublication(lambda: cast(SocialUnitOfWork, uow)).execute(
            Actor(user_id="user_2", organization_id="org_2", role=OrganizationRole.ADMIN),
            publication.id,
        )

    assert publication.status == PublicationStatus.SCHEDULED
    assert uow.committed is False


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
        caption="Kinetic Mobiles reminds customers to back up their device before repair.",
        status=status,
    )


class CancelPublicationUow:
    def __init__(self, workspace: Workspace, publication: Publication) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.publications = PublicationRepo(publication)
        self.committed = False

    async def __aenter__(self) -> "CancelPublicationUow":
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
