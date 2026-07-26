from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

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
        self._access_key_id = _require(settings.aws_access_key_id, "AWS_ACCESS_KEY_ID")
        self._secret_access_key = _require(settings.aws_secret_access_key, "AWS_SECRET_ACCESS_KEY")

    def create_upload_target(self, request: MediaUploadRequest) -> MediaUploadTarget:
        now = datetime.now(UTC)
        expires_in = self._settings.media_upload_url_ttl_seconds
        object_key = _object_key(request)
        upload_url = self._presign_put_url(
            object_key=object_key,
            content_type=request.content_type,
            checksum_sha256=request.checksum_sha256,
            now=now,
            expires_in=expires_in,
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

    def _presign_put_url(
        self,
        *,
        object_key: str,
        content_type: str,
        checksum_sha256: str,
        now: datetime,
        expires_in: int,
    ) -> str:
        host = f"{self._bucket}.s3.{self._region}.amazonaws.com"
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{self._region}/s3/aws4_request"
        signed_headers = "content-type;host;x-amz-content-sha256;x-amz-meta-sha256"
        query_params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self._access_key_id}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires_in),
            "X-Amz-SignedHeaders": signed_headers,
        }
        if self._settings.aws_session_token:
            query_params["X-Amz-Security-Token"] = self._settings.aws_session_token

        canonical_uri = f"/{_quote_s3_key(object_key)}"
        canonical_query_string = _canonical_query_string(query_params)
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{host}\n"
            "x-amz-content-sha256:UNSIGNED-PAYLOAD\n"
            f"x-amz-meta-sha256:{checksum_sha256}\n"
        )
        canonical_request = "\n".join(
            [
                "PUT",
                canonical_uri,
                canonical_query_string,
                canonical_headers,
                signed_headers,
                "UNSIGNED-PAYLOAD",
            ]
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signing_key = _signing_key(self._secret_access_key, date_stamp, self._region)
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        return f"https://{host}{canonical_uri}?{canonical_query_string}&X-Amz-Signature={signature}"


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


def _canonical_query_string(params: dict[str, str]) -> str:
    return urlencode(sorted(params.items()), quote_via=quote, safe="-_.~")


def _quote_s3_key(value: str) -> str:
    return quote(value, safe="/-_.~")


def _signing_key(secret_access_key: str, date_stamp: str, region: str) -> bytes:
    date_key = _sign(("AWS4" + secret_access_key).encode(), date_stamp)
    date_region_key = _sign(date_key, region)
    date_region_service_key = _sign(date_region_key, "s3")
    return _sign(date_region_service_key, "aws4_request")


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()
