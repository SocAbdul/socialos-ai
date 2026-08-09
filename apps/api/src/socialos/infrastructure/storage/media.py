from __future__ import annotations

import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import boto3
import httpx
from botocore.client import Config
from botocore.exceptions import ClientError

from socialos.application.social.ports import (
    MediaUploadRequest,
    MediaUploadTarget,
    StoredMedia,
    StoredObjectMetadata,
)
from socialos.config import Settings
from socialos.domain.social import MediaAsset


class MediaStorageConfigurationError(RuntimeError):
    """Raised when media storage is not configured safely."""


class HTTPMediaPreflightService:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._allowed_base = settings.resolved_media_public_base_url + "/"
        self._transport = transport

    async def validate(self, media: MediaAsset) -> None:
        url = media.storage_url
        if not url.startswith(self._allowed_base) or not url.startswith("https://"):
            raise ValueError("Media URL is not an approved public HTTPS asset")
        async with httpx.AsyncClient(
            timeout=8, follow_redirects=False, transport=self._transport
        ) as client:
            response = await client.head(url)
        if response.status_code != 200:
            raise ValueError("Media is not publicly accessible; publication was not queued")
        expected_type = media.content_type
        if response.headers.get("content-type", "").split(";", 1)[0] != expected_type:
            raise ValueError("Public media Content-Type does not match the uploaded asset")
        length = response.headers.get("content-length")
        if length is None or int(length) != media.size_bytes:
            raise ValueError("Public media size does not match the uploaded asset")


class LocalMediaStorageService:
    """Legacy non-uploading storage contract retained for local API contract tests."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        object_key = _object_key(request)
        return MediaUploadTarget(
            object_key=object_key,
            upload_url=f"{str(self._settings.api_base_url).rstrip('/')}/local-media/{quote(object_key)}",
            public_url=self.public_url(object_key),
            method="PUT",
            headers={
                "Content-Type": request.content_type,
                "x-amz-meta-sha256": request.checksum_sha256,
            },
            expires_at=now + timedelta(seconds=self._settings.media_upload_url_ttl_seconds),
            max_size_bytes=self._settings.media_max_upload_bytes,
        )

    def store(self, request: MediaUploadRequest, content: bytes) -> StoredMedia:
        raise MediaStorageConfigurationError(
            "Direct media upload requires MEDIA_STORAGE_PROVIDER=local-public"
        )

    def delete(self, object_key: str) -> None:
        raise MediaStorageConfigurationError("Legacy local storage does not persist objects")

    def exists(self, object_key: str) -> bool:
        return False

    def public_url(self, object_key: str) -> str:
        return f"{self._settings.media_public_base_url.rstrip('/')}/{quote(object_key)}"

    def metadata(self, object_key: str) -> StoredObjectMetadata | None:
        return None


class LocalPublicMediaStorageService:
    """Persistent, opaque-key local storage for zero-cost preview environments."""

    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.local_media_root).resolve()
        self._public_base_url = settings.media_public_base_url.rstrip("/")
        if not self._public_base_url.startswith("https://"):
            raise MediaStorageConfigurationError("MEDIA_PUBLIC_BASE_URL must use HTTPS")

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        object_key = _random_object_key(request)
        return MediaUploadTarget(
            object_key=object_key,
            upload_url="",
            public_url=f"{self._public_base_url}/{quote(object_key)}",
            method="POST",
            headers={"Content-Type": request.content_type},
            expires_at=now + timedelta(minutes=15),
            max_size_bytes=request.size_bytes,
        )

    def store(self, request: MediaUploadRequest, content: bytes) -> StoredMedia:
        if hashlib.sha256(content).hexdigest() != request.checksum_sha256:
            raise ValueError("Media checksum does not match the uploaded file")
        object_key = _random_object_key(request)
        destination = (self._root / object_key).resolve()
        if not destination.is_relative_to(self._root):
            raise ValueError("Invalid media storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + f".{secrets.token_hex(8)}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(content)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredMedia(
            storage_provider="local-public",
            storage_key=object_key,
            public_url=f"{self._public_base_url}/{quote(object_key)}",
            content_type=request.content_type,
            checksum_sha256=request.checksum_sha256,
            size_bytes=len(content),
        )

    def delete(self, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)

    def exists(self, object_key: str) -> bool:
        return self._path(object_key).is_file()

    def public_url(self, object_key: str) -> str:
        return f"{self._public_base_url}/{quote(object_key)}"

    def metadata(self, object_key: str) -> StoredObjectMetadata | None:
        path = self._path(object_key)
        if not path.is_file():
            return None
        content = path.read_bytes()
        return StoredObjectMetadata(
            object_key=object_key,
            content_type=_content_type(path.suffix),
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        )

    def _path(self, object_key: str) -> Path:
        path = (self._root / object_key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("Invalid media storage path")
        return path


class S3MediaStorageService:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
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
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = str(settings.s3_endpoint_url)
        self._client: Any = client or boto3.client("s3", **client_kwargs)

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        expires_in = self._settings.media_upload_url_ttl_seconds
        object_key = _random_object_key(request)
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

    def store(self, request: MediaUploadRequest, content: bytes) -> StoredMedia:
        raise MediaStorageConfigurationError("Direct API upload is only available for local-public")

    def delete(self, object_key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=object_key)

    def exists(self, object_key: str) -> bool:
        return self.metadata(object_key) is not None

    def public_url(self, object_key: str) -> str:
        return f"{self._public_base_url}/{quote(object_key)}"

    def metadata(self, object_key: str) -> StoredObjectMetadata | None:
        try:
            result = self._client.head_object(Bucket=self._bucket, Key=object_key)
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return None
            raise
        metadata = result.get("Metadata", {})
        return StoredObjectMetadata(
            object_key=object_key,
            content_type=result.get("ContentType", "application/octet-stream"),
            size_bytes=result.get("ContentLength", 0),
            checksum_sha256=metadata.get("sha256"),
        )


def build_media_storage(
    settings: Settings,
) -> LocalMediaStorageService | LocalPublicMediaStorageService | S3MediaStorageService:
    if settings.media_storage_provider == "s3":
        return S3MediaStorageService(settings)
    if settings.media_storage_provider == "local-public":
        return LocalPublicMediaStorageService(settings)
    return LocalMediaStorageService(settings)


def _object_key(request: MediaUploadRequest) -> str:
    extension = _extension(request.content_type)
    filename = f"{request.checksum_sha256[:16]}-{request.size_bytes}.{extension}"
    return f"workspaces/{request.workspace_id}/media/{filename}"


def _random_object_key(request: MediaUploadRequest) -> str:
    filename = f"{secrets.token_urlsafe(32)}.{_extension(request.content_type)}"
    return f"workspaces/{request.workspace_id}/media/{filename}"


def _extension(content_type: str) -> str:
    return {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4"}.get(content_type, "bin")


def _content_type(suffix: str) -> str:
    return {".jpg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4"}.get(
        suffix.lower(), "application/octet-stream"
    )


def _require(value: str | None, name: str) -> str:
    if not value:
        raise MediaStorageConfigurationError(f"{name} is required for S3 media storage")
    return value
