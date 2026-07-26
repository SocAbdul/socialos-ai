from uuid import uuid4

from socialos.application.social.ports import MediaUploadRequest
from socialos.config import Settings
from socialos.infrastructure.storage.media import (
    LocalMediaStorageService,
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
