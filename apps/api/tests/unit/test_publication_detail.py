from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import ApplicationNotFoundError, GetPublicationDetail
from socialos.domain.social import (
    AttemptStatus,
    Platform,
    Publication,
    PublicationAttempt,
    PublicationStatus,
    Workspace,
)


@pytest.mark.asyncio
async def test_get_publication_detail_returns_attempt_history_for_actor_workspace() -> None:
    workspace = Workspace(
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )
    publication = Publication(
        workspace_id=workspace.id,
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.FACEBOOK,
        caption="Kinetic Mobiles launches same-day screen repairs in Valencia.",
        status=PublicationStatus.PUBLISHED,
        external_publication_id="fb_post_123",
        external_url="https://facebook.com/kineticmobiles/posts/fb_post_123",
    )
    older_attempt = PublicationAttempt(
        publication_id=publication.id,
        attempt_number=1,
        status=AttemptStatus.FAILED_RETRYABLE,
        provider="meta",
        error_code="RATE_LIMIT",
        error_message="Meta temporary rate limit",
        created_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    newer_attempt = PublicationAttempt(
        publication_id=publication.id,
        attempt_number=2,
        status=AttemptStatus.SUCCEEDED,
        provider="meta",
        request_id="req_123",
        external_publication_id="fb_post_123",
        created_at=datetime.now(UTC),
    )
    uow = PublicationDetailUow(
        workspace=workspace,
        publication=publication,
        attempts=[older_attempt, newer_attempt],
    )

    detail = await GetPublicationDetail(lambda: cast(SocialUnitOfWork, uow)).execute(
        actor=Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN),
        publication_id=publication.id,
    )

    assert detail.publication == publication
    assert [attempt.attempt_number for attempt in detail.attempts] == [2, 1]
    assert detail.attempts[0].external_publication_id == "fb_post_123"


@pytest.mark.asyncio
async def test_get_publication_detail_hides_publications_from_other_workspaces() -> None:
    workspace = Workspace(
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )
    publication = Publication(
        workspace_id=workspace.id,
        content_item_id=uuid4(),
        platform_connection_id=uuid4(),
        social_account_id=uuid4(),
        platform=Platform.INSTAGRAM,
        caption="Premium refurbished phones, tested by Kinetic Mobiles technicians.",
        status=PublicationStatus.FAILED_RETRYABLE,
    )
    uow = PublicationDetailUow(workspace=workspace, publication=publication, attempts=[])

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await GetPublicationDetail(lambda: cast(SocialUnitOfWork, uow)).execute(
            actor=Actor(user_id="user_2", organization_id="org_2", role=OrganizationRole.ADMIN),
            publication_id=publication.id,
        )


class PublicationDetailUow:
    def __init__(
        self,
        workspace: Workspace,
        publication: Publication,
        attempts: list[PublicationAttempt],
    ) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.publications = PublicationRepo(publication)
        self.publication_attempts = PublicationAttemptRepo(attempts)

    async def __aenter__(self) -> "PublicationDetailUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class WorkspaceRepo:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        if self._workspace.id != workspace_id:
            return None
        return self._workspace

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


class PublicationAttemptRepo:
    def __init__(self, attempts: list[PublicationAttempt]) -> None:
        self._attempts = attempts

    async def list_for_publication(self, publication_id: UUID) -> list[PublicationAttempt]:
        attempts = [
            attempt for attempt in self._attempts if attempt.publication_id == publication_id
        ]
        return sorted(attempts, key=lambda attempt: attempt.created_at, reverse=True)
