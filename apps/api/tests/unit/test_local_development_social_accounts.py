from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialProvider, SocialUnitOfWork
from socialos.application.social.use_cases import (
    EnsureLocalDevelopmentSocialAccounts,
    LocalDevelopmentConnectionError,
    PublishQueuedPublication,
)
from socialos.domain.social import (
    AttemptStatus,
    Platform,
    PlatformConnection,
    Publication,
    PublicationAttempt,
    PublicationStatus,
    SocialAccount,
    Workspace,
)
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.local_dev import LocalDevelopmentSocialProvider


@pytest.mark.asyncio
async def test_local_development_accounts_are_blocked_outside_local_development() -> None:
    uow = LocalDevelopmentUow(make_workspace())

    with pytest.raises(LocalDevelopmentConnectionError, match="ENVIRONMENT=local"):
        await EnsureLocalDevelopmentSocialAccounts(
            lambda: cast(SocialUnitOfWork, uow),
            FernetTokenCipher("test-key"),
            environment="staging",
            auth_mode="clerk",
        ).execute(make_actor(), uow.workspace.id)

    assert uow.connections == []
    assert uow.accounts == []


@pytest.mark.asyncio
async def test_local_development_accounts_are_idempotent_and_workspace_scoped() -> None:
    workspace = make_workspace()
    other_workspace = make_workspace()
    uow = LocalDevelopmentUow(workspace)
    uow.connections.append(
        PlatformConnection(
            workspace_id=other_workspace.id,
            provider="local-dev",
            platform=Platform.FACEBOOK,
            external_account_id="local-dev-facebook-page",
            external_account_name="Other workspace",
            encrypted_credentials="encrypted",
            scopes=[],
            capabilities={},
        )
    )

    use_case = EnsureLocalDevelopmentSocialAccounts(
        lambda: cast(SocialUnitOfWork, uow),
        FernetTokenCipher("test-key"),
        environment="local",
        auth_mode="development",
    )
    first = await use_case.execute(make_actor(), workspace.id)
    second = await use_case.execute(make_actor(), workspace.id)

    assert len(first.connections) == 2
    assert len(first.accounts) == 2
    assert [connection.id for connection in first.connections] == [
        connection.id for connection in second.connections
    ]
    assert len([item for item in uow.connections if item.workspace_id == workspace.id]) == 2
    assert len([item for item in uow.connections if item.workspace_id == other_workspace.id]) == 1
    assert all(account.safe_metadata["development_only"] for account in first.accounts)


@pytest.mark.asyncio
async def test_local_development_provider_records_successful_publication_attempts() -> None:
    workspace = make_workspace()
    uow = LocalDevelopmentUow(workspace)
    result = await EnsureLocalDevelopmentSocialAccounts(
        lambda: cast(SocialUnitOfWork, uow),
        FernetTokenCipher("test-key"),
        environment="local",
        auth_mode="development",
    ).execute(make_actor(), workspace.id)
    account = next(account for account in result.accounts if account.platform == Platform.FACEBOOK)
    publication = Publication(
        workspace_id=workspace.id,
        content_item_id=uuid4(),
        platform_connection_id=account.platform_connection_id,
        social_account_id=account.id,
        platform=Platform.FACEBOOK,
        caption="Kinetic Mobiles same-day repairs are live.",
        status=PublicationStatus.QUEUED,
    )
    uow.publication = publication

    published = await PublishQueuedPublication(
        lambda: cast(SocialUnitOfWork, uow),
        {"local-dev": cast(SocialProvider, LocalDevelopmentSocialProvider())},
    ).execute(publication.id)

    assert published is not None
    assert published.status == PublicationStatus.PUBLISHED
    assert published.external_publication_id is not None
    assert published.external_publication_id.startswith("local-dev-facebook-")
    assert [attempt.status for attempt in uow.attempts] == [
        AttemptStatus.STARTED,
        AttemptStatus.SUCCEEDED,
    ]
    assert uow.attempts[-1].provider == "local-dev"


def make_workspace() -> Workspace:
    return Workspace(
        owner_id="user_local_founder",
        external_organization_id="org_local_socialos",
        name="Kinetic Mobiles",
    )


def make_actor() -> Actor:
    return Actor(
        user_id="user_local_founder",
        organization_id="org_local_socialos",
        role=OrganizationRole.ADMIN,
    )


class LocalDevelopmentUow:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.connections: list[PlatformConnection] = []
        self.accounts: list[SocialAccount] = []
        self.attempts: list[PublicationAttempt] = []
        self.publication: Publication | None = None
        self.workspaces = WorkspaceRepo(workspace)
        self.platform_connections = PlatformConnectionRepo(self.connections)
        self.social_accounts = SocialAccountRepo(self.accounts)
        self.publications = PublicationRepo(self)
        self.publication_attempts = PublicationAttemptRepo(self.attempts)

    async def __aenter__(self) -> "LocalDevelopmentUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class WorkspaceRepo:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


class PlatformConnectionRepo:
    def __init__(self, items: list[PlatformConnection]) -> None:
        self._items = items

    async def add(self, connection: PlatformConnection) -> PlatformConnection:
        self._items.append(connection)
        return connection

    async def get(self, connection_id: UUID, workspace_id: UUID) -> PlatformConnection | None:
        return next(
            (
                item
                for item in self._items
                if item.id == connection_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[PlatformConnection]:
        return [item for item in self._items if item.workspace_id == workspace_id]


class SocialAccountRepo:
    def __init__(self, items: list[SocialAccount]) -> None:
        self._items = items

    async def add(self, account: SocialAccount) -> SocialAccount:
        self._items.append(account)
        return account

    async def get(self, account_id: UUID, workspace_id: UUID) -> SocialAccount | None:
        return next(
            (
                item
                for item in self._items
                if item.id == account_id and item.workspace_id == workspace_id
            ),
            None,
        )

    async def list_for_connection(self, connection_id: UUID) -> Sequence[SocialAccount]:
        return [item for item in self._items if item.platform_connection_id == connection_id]

    async def list_for_workspace(self, workspace_id: UUID) -> Sequence[SocialAccount]:
        return [item for item in self._items if item.workspace_id == workspace_id]


class PublicationRepo:
    def __init__(self, uow: LocalDevelopmentUow) -> None:
        self._uow = uow

    async def get_for_update(self, publication_id: UUID) -> Publication | None:
        publication = self._uow.publication
        if publication and publication.id == publication_id:
            return publication
        return None

    async def update(self, publication: Publication) -> Publication:
        self._uow.publication = publication
        return publication


class PublicationAttemptRepo:
    def __init__(self, items: list[PublicationAttempt]) -> None:
        self._items = items

    async def add(self, attempt: PublicationAttempt) -> PublicationAttempt:
        self._items.append(attempt)
        return attempt

    async def list_for_publication(self, publication_id: UUID) -> Sequence[PublicationAttempt]:
        return [item for item in self._items if item.publication_id == publication_id]

    async def count_for_publication(self, publication_id: UUID) -> int:
        return max(
            (item.attempt_number for item in self._items if item.publication_id == publication_id),
            default=0,
        )
