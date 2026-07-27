from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import ApplicationNotFoundError, ListContentItems
from socialos.domain.social import ContentItem, Workspace


@pytest.mark.asyncio
async def test_list_content_items_returns_workspace_items_newest_first() -> None:
    workspace = make_workspace()
    old_item = ContentItem(
        workspace_id=workspace.id,
        campaign_id=uuid4(),
        author_id="user_1",
        body="Kinetic Mobiles now offers battery health checks for busy professionals.",
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    new_item = ContentItem(
        workspace_id=workspace.id,
        campaign_id=uuid4(),
        author_id="user_1",
        body="Same-day screen replacement slots are available this Friday.",
        created_at=datetime.now(UTC),
    )
    other_workspace_item = ContentItem(
        workspace_id=uuid4(),
        campaign_id=uuid4(),
        author_id="user_2",
        body="Other workspace content should stay hidden.",
    )
    uow = ContentItemListingUow(
        workspace=workspace,
        content_items=[old_item, new_item, other_workspace_item],
    )

    items = await ListContentItems(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), workspace.id
    )

    assert [item.body for item in items] == [
        "Same-day screen replacement slots are available this Friday.",
        "Kinetic Mobiles now offers battery health checks for busy professionals.",
    ]


@pytest.mark.asyncio
async def test_list_content_items_hides_other_tenant_workspace() -> None:
    workspace = make_workspace()
    uow = ContentItemListingUow(workspace=workspace, content_items=[])

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await ListContentItems(lambda: cast(SocialUnitOfWork, uow)).execute(
            Actor(user_id="user_2", organization_id="org_2", role=OrganizationRole.ADMIN),
            workspace.id,
        )


def make_workspace() -> Workspace:
    return Workspace(
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )


def make_actor() -> Actor:
    return Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN)


class ContentItemListingUow:
    def __init__(self, workspace: Workspace, content_items: list[ContentItem]) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.content_items = ContentItemRepo(content_items)

    async def __aenter__(self) -> "ContentItemListingUow":
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


class ContentItemRepo:
    def __init__(self, content_items: list[ContentItem]) -> None:
        self._content_items = content_items

    async def list_for_workspace(self, workspace_id: UUID) -> list[ContentItem]:
        items = [item for item in self._content_items if item.workspace_id == workspace_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)
