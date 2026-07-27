from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import ApplicationNotFoundError, ListMediaAssets
from socialos.domain.social import MediaAsset, MediaType, Workspace


@pytest.mark.asyncio
async def test_list_media_assets_returns_workspace_assets_newest_first() -> None:
    workspace = make_workspace()
    old_asset = MediaAsset(
        workspace_id=workspace.id,
        uploader_id="user_1",
        media_type=MediaType.IMAGE,
        storage_url="https://cdn.socialos.local/kinetic/old-repair-photo.jpg",
        content_type="image/jpeg",
        checksum_sha256="a" * 64,
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    new_asset = MediaAsset(
        workspace_id=workspace.id,
        uploader_id="user_1",
        media_type=MediaType.IMAGE,
        storage_url="https://cdn.socialos.local/kinetic/new-screen-repair.jpg",
        content_type="image/jpeg",
        checksum_sha256="b" * 64,
        created_at=datetime.now(UTC),
    )
    other_workspace_asset = MediaAsset(
        workspace_id=uuid4(),
        uploader_id="user_2",
        media_type=MediaType.IMAGE,
        storage_url="https://cdn.socialos.local/other/hidden.jpg",
        content_type="image/jpeg",
        checksum_sha256="c" * 64,
    )
    uow = MediaAssetListingUow(
        workspace=workspace,
        media_assets=[old_asset, new_asset, other_workspace_asset],
    )

    assets = await ListMediaAssets(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), workspace.id
    )

    assert [asset.storage_url for asset in assets] == [
        "https://cdn.socialos.local/kinetic/new-screen-repair.jpg",
        "https://cdn.socialos.local/kinetic/old-repair-photo.jpg",
    ]


@pytest.mark.asyncio
async def test_list_media_assets_hides_other_tenant_workspace() -> None:
    workspace = make_workspace()
    uow = MediaAssetListingUow(workspace=workspace, media_assets=[])

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await ListMediaAssets(lambda: cast(SocialUnitOfWork, uow)).execute(
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


class MediaAssetListingUow:
    def __init__(self, workspace: Workspace, media_assets: list[MediaAsset]) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.media_assets = MediaAssetRepo(media_assets)

    async def __aenter__(self) -> "MediaAssetListingUow":
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


class MediaAssetRepo:
    def __init__(self, media_assets: list[MediaAsset]) -> None:
        self._media_assets = media_assets

    async def list_for_workspace(self, workspace_id: UUID) -> list[MediaAsset]:
        assets = [asset for asset in self._media_assets if asset.workspace_id == workspace_id]
        return sorted(assets, key=lambda asset: asset.created_at, reverse=True)
