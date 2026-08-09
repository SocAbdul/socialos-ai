from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import (
    MediaStorageService,
    MediaUploadRequest,
    MediaUploadTarget,
    SocialUnitOfWork,
)
from socialos.application.social.use_cases import (
    RegisterMediaAsset,
    RegisterMediaAssetCommand,
    RequestMediaUpload,
    RequestMediaUploadCommand,
)
from socialos.domain.social import MediaType, Workspace


@pytest.mark.asyncio
async def test_request_media_upload_returns_storage_target() -> None:
    workspace_id = uuid4()
    storage = FakeMediaStorage()
    result = await RequestMediaUpload(
        lambda: cast(SocialUnitOfWork, MediaUploadUow(workspace_id)),
        cast(MediaStorageService, storage),
    ).execute(
        Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN),
        RequestMediaUploadCommand(
            workspace_id=workspace_id,
            media_type=MediaType.IMAGE,
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
            size_bytes=1_024,
        ),
    )

    assert result.public_url == "https://media.example.test/image.jpg"
    assert storage.request is not None
    assert storage.request.workspace_id == workspace_id
    assert storage.request.uploader_id == "user_1"


@pytest.mark.asyncio
async def test_request_media_upload_rejects_unsupported_content_type() -> None:
    workspace_id = uuid4()

    with pytest.raises(ValueError, match="Unsupported media content type"):
        await RequestMediaUpload(
            lambda: cast(SocialUnitOfWork, MediaUploadUow(workspace_id)),
            cast(MediaStorageService, FakeMediaStorage()),
        ).execute(
            Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN),
            RequestMediaUploadCommand(
                workspace_id=workspace_id,
                media_type=MediaType.IMAGE,
                content_type="image/gif",
                checksum_sha256="a" * 64,
                size_bytes=1_024,
            ),
        )


@pytest.mark.asyncio
async def test_registered_storage_key_must_belong_to_workspace() -> None:
    workspace_id = uuid4()
    foreign_workspace_id = uuid4()

    with pytest.raises(ValueError, match="does not belong to this workspace"):
        await RegisterMediaAsset(lambda: cast(SocialUnitOfWork, None)).execute(
            Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN),
            RegisterMediaAssetCommand(
                workspace_id=workspace_id,
                media_type=MediaType.IMAGE,
                storage_url="https://media.example.test/image.jpg",
                content_type="image/jpeg",
                checksum_sha256="a" * 64,
                storage_provider="s3",
                storage_key=f"workspaces/{foreign_workspace_id}/media/image.jpg",
                size_bytes=1_024,
            ),
        )


class FakeMediaStorage:
    def __init__(self) -> None:
        self.request: MediaUploadRequest | None = None

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        self.request = request
        return MediaUploadTarget(
            object_key="workspaces/workspace/media/image.jpg",
            upload_url="https://s3.example.test/upload",
            public_url="https://media.example.test/image.jpg",
            method="PUT",
            headers={"Content-Type": request.content_type},
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
            max_size_bytes=15 * 1024 * 1024,
        )


class MediaUploadUow:
    def __init__(self, workspace_id: UUID) -> None:
        self.workspaces = WorkspaceRepo(workspace_id)

    async def __aenter__(self) -> "MediaUploadUow":
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
