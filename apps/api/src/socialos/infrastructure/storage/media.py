from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import boto3
from botocore.client import Config

from socialos.application.social.ports import MediaUploadRequest, MediaUploadTarget
from socialos.config import Settings


class MediaStorageConfigurationError(RuntimeError):
    """Raised when media storage is not configured safely."""


class LocalMediaStorageService:
    """Development-only media storage target.

    The returned URL is intentionally non-uploading. It lets local API clients exercise the
    same contract as S3 without requiring AWS credentials.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        object_key = _object_key(request)
        return MediaUploadTarget(
            object_key=object_key,
            upload_url=f"http://localhost:8000/local-media/{quote(object_key)}",
            public_url=f"https://media.local.socialos.invalid/{quote(object_key)}",
            method="PUT",
            headers={
                "Content-Type": request.content_type,
                "x-amz-meta-sha256": request.checksum_sha256,
            },
            expires_at=now + timedelta(seconds=self._settings.media_upload_url_ttl_seconds),
            max_size_bytes=self._settings.media_max_upload_bytes,
        )


class S3MediaStorageService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bucket = _require(settings.s3_media_bucket, "S3_MEDIA_BUCKET")
        self._region = _require(settings.s3_media_region, "S3_MEDIA_REGION")
        self._public_base_url = _require(
            settings.s3_media_public_base_url, "S3_MEDIA_PUBLIC_BASE_URL"
        ).rstrip("/")
        client_kwargs: dict[str, object] = {
            "region_name": self._region,
            "config": Config(signature_version="s3v4"),
        }
        if settings.aws_access_key_id:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            client_kwargs["aws_session_token"] = settings.aws_session_token
        self._client = boto3.client("s3", **client_kwargs)

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        expires_in = self._settings.media_upload_url_ttl_seconds
        object_key = _object_key(request)
        upload_url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": object_key,
                "ContentType": request.content_type,
                "Metadata": {"sha256": request.checksum_sha256},
            },
            ExpiresIn=expires_in,
            HttpMethod="PUT",
        )
        return MediaUploadTarget(
            object_key=object_key,
            upload_url=upload_url,
            public_url=f"{self._public_base_url}/{quote(object_key)}",
            method="PUT",
            headers={
                "Content-Type": request.content_type,
                "x-amz-meta-sha256": request.checksum_sha256,
            },
            expires_at=now + timedelta(seconds=expires_in),
            max_size_bytes=self._settings.media_max_upload_bytes,
        )


def build_media_storage(settings: Settings) -> LocalMediaStorageService | S3MediaStorageService:
    if settings.media_storage_provider == "s3":
        return S3MediaStorageService(settings)
    return LocalMediaStorageService(settings)


def _object_key(request: MediaUploadRequest) -> str:
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "video/mp4": "mp4",
    }.get(request.content_type, "bin")
    return (
        f"workspaces/{request.workspace_id}/media/"
        f"{request.checksum_sha256[:16]}-{request.size_bytes}.{extension}"
    )


def _require(value: str | None, name: str) -> str:
    if not value:
        raise MediaStorageConfigurationError(f"{name} is required for S3 media storage")
    return value
