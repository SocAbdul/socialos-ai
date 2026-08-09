import hashlib
from pathlib import Path
from uuid import uuid4

import boto3
import pytest
from botocore.stub import Stubber

from socialos.application.social.ports import MediaUploadRequest
from socialos.config import Settings
from socialos.infrastructure.storage.media import (
    LocalMediaStorageService,
    LocalPublicMediaStorageService,
    S3MediaStorageService,
    build_media_storage,
)


def make_upload_request() -> MediaUploadRequest:
    return MediaUploadRequest(
        workspace_id=uuid4(),
        uploader_id="user_123",
        media_type="image",
        content_type="image/jpeg",
        checksum_sha256="a" * 64,
        size_bytes=1_024,
    )


def test_local_media_storage_returns_development_target() -> None:
    service = LocalMediaStorageService(Settings(environment="local"))

    target = service.create_upload_target(make_upload_request())

    assert target.method == "PUT"
    assert target.headers["Content-Type"] == "image/jpeg"
    assert target.public_url.startswith("https://media.local.socialos.invalid/")
    assert target.max_size_bytes == 15 * 1024 * 1024


def test_s3_media_storage_returns_presigned_put_target_without_leaking_secret() -> None:
    settings = Settings(
        environment="local",
        media_storage_provider="s3",
        s3_media_bucket="socialos-media-test",
        s3_media_region="eu-west-2",
        s3_media_public_base_url="https://media.example.test",
        aws_access_key_id="AKIATEST",
        aws_secret_access_key="super-secret-value",  # noqa: S106 - fake unit-test secret
    )
    service = S3MediaStorageService(settings)

    target = service.create_upload_target(make_upload_request())

    assert target.method == "PUT"
    assert target.public_url.startswith("https://media.example.test/workspaces/")
    assert "X-Amz-Signature=" in target.upload_url
    assert "X-Amz-Credential=AKIATEST" in target.upload_url
    assert "super-secret-value" not in target.upload_url
    assert target.headers == {
        "Content-Type": "image/jpeg",
        "x-amz-meta-sha256": "a" * 64,
    }


def test_build_media_storage_uses_configured_provider() -> None:
    local = build_media_storage(Settings(environment="local", media_storage_provider="local"))
    s3 = build_media_storage(
        Settings(
            environment="local",
            media_storage_provider="s3",
            s3_media_bucket="socialos-media-test",
            s3_media_region="eu-west-2",
            s3_media_public_base_url="https://media.example.test",
            aws_access_key_id="AKIATEST",
            aws_secret_access_key="super-secret-value",  # noqa: S106 - fake unit-test secret
        )
    )

    assert isinstance(local, LocalMediaStorageService)
    assert isinstance(s3, S3MediaStorageService)


def test_local_public_storage_persists_under_opaque_unique_keys(tmp_path: Path) -> None:
    settings = Settings(
        environment="local",
        media_storage_provider="local-public",
        local_media_root=str(tmp_path),
        media_public_base_url="https://preview.example.test/media",
    )
    service = LocalPublicMediaStorageService(settings)
    content = b"\x89PNG\r\n\x1a\nreal-image-payload"
    request = MediaUploadRequest(
        workspace_id=uuid4(),
        uploader_id="user_123",
        media_type="image",
        content_type="image/png",
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )

    first = service.store(request, content)
    second = service.store(request, content)

    assert first.storage_key != second.storage_key
    assert request.checksum_sha256[:16] not in first.storage_key
    assert (tmp_path / first.storage_key).read_bytes() == content
    assert first.public_url.startswith("https://preview.example.test/media/workspaces/")


def test_local_public_storage_rejects_checksum_mismatch(tmp_path: Path) -> None:
    service = LocalPublicMediaStorageService(
        Settings(
            environment="local",
            media_storage_provider="local-public",
            local_media_root=str(tmp_path),
            media_public_base_url="https://preview.example.test/media",
        )
    )
    request = make_upload_request()

    with pytest.raises(ValueError, match="checksum"):
        service.store(request, b"different")


def test_local_public_storage_supports_metadata_exists_and_delete(tmp_path: Path) -> None:
    service = LocalPublicMediaStorageService(
        Settings(
            environment="local",
            media_storage_provider="local-public",
            local_media_root=str(tmp_path),
            media_public_base_url="https://preview.example.test/media",
        )
    )
    content = b"\x89PNG\r\n\x1a\nportable"
    request = MediaUploadRequest(
        workspace_id=uuid4(),
        uploader_id="user_123",
        media_type="image",
        content_type="image/png",
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )

    stored = service.store(request, content)
    metadata = service.metadata(stored.storage_key)

    assert service.exists(stored.storage_key)
    assert metadata is not None
    assert metadata.checksum_sha256 == request.checksum_sha256
    assert service.public_url(stored.storage_key) == stored.public_url
    service.delete(stored.storage_key)
    assert not service.exists(stored.storage_key)


def test_local_storage_rejects_keys_outside_configured_root(tmp_path: Path) -> None:
    service = LocalPublicMediaStorageService(
        Settings(
            environment="local",
            media_storage_provider="local-public",
            local_media_root=str(tmp_path),
            media_public_base_url="https://preview.example.test/media",
        )
    )

    with pytest.raises(ValueError, match="Invalid media storage path"):
        service.exists("../../outside.jpg")


def test_s3_compatible_storage_uses_custom_endpoint_and_object_operations() -> None:
    client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url="https://objects.example.test",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",  # noqa: S106
    )
    stubber = Stubber(client)
    key = "workspaces/workspace-1/media/object.jpg"
    stubber.add_response(
        "head_object",
        {
            "ContentLength": 128,
            "ContentType": "image/jpeg",
            "Metadata": {"sha256": "a" * 64},
        },
        {"Bucket": "media", "Key": key},
    )
    stubber.add_response("delete_object", {}, {"Bucket": "media", "Key": key})
    service = S3MediaStorageService(
        Settings(
            environment="local",
            media_storage_provider="s3",
            s3_media_bucket="media",
            s3_media_region="auto",
            s3_media_public_base_url="https://media.example.test",
            s3_endpoint_url="https://objects.example.test",
        ),
        client=client,
    )

    with stubber:
        metadata = service.metadata(key)
        service.delete(key)

    assert metadata is not None
    assert metadata.size_bytes == 128
    assert metadata.checksum_sha256 == "a" * 64
    assert service.public_url(key) == f"https://media.example.test/{key}"
