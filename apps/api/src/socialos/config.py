import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
AuthMode = Literal["development", "clerk"]
MediaStorageProvider = Literal["local", "local-public", "s3"]
SocialProviderMode = Literal["local-dev", "meta"]

_MIN_TOKEN_ENCRYPTION_KEY_LENGTH = 32
_INSECURE_TOKEN_ENCRYPTION_KEYS = frozenset(
    {
        "replace-with-a-long-random-secret",
        "local-development-token-encryption-key",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SocialOS AI"
    environment: Environment = "local"
    log_level: str = "INFO"
    release_sha: str = "development"
    app_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    web_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    api_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    database_url: str = "postgresql+asyncpg://socialos:socialos@localhost:5432/socialos"
    redis_url: str = "redis://localhost:6379/0"
    auth_mode: AuthMode = "development"
    clerk_jwks_url: AnyHttpUrl | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None
    clerk_authorized_parties: str = "http://localhost:3000"
    web_origins: str = "http://localhost:3000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    token_encryption_key: str | None = Field(default=None, repr=False)
    meta_app_id: str | None = None
    meta_app_secret: str | None = Field(default=None, repr=False)
    meta_login_config_id: str | None = None
    meta_redirect_uri: str | None = None
    meta_graph_api_version: str = "v25.0"
    social_provider: SocialProviderMode = "local-dev"
    social_provider_meta_enabled: bool = True
    social_provider_linkedin_enabled: bool = False
    social_provider_youtube_enabled: bool = False
    social_provider_tiktok_enabled: bool = False
    social_provider_reddit_enabled: bool = False
    ai_provider: str = "local"
    ai_model: str = "socialos-local-v1"
    media_storage_provider: MediaStorageProvider = "local"
    local_media_root: str = "/data/public-media"
    media_public_base_url: str = "https://media.local.socialos.invalid/media"
    media_upload_url_ttl_seconds: int = 900
    media_max_upload_bytes: int = 15 * 1024 * 1024
    s3_media_bucket: str | None = None
    s3_media_region: str | None = None
    s3_media_public_base_url: str | None = None
    s3_endpoint_url: AnyHttpUrl | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = Field(default=None, repr=False)
    aws_session_token: str | None = Field(default=None, repr=False)
    database_pool_size: int = 10
    database_max_overflow: int = 20

    @field_validator(
        "clerk_jwks_url",
        "clerk_issuer",
        "clerk_audience",
        "token_encryption_key",
        "meta_app_id",
        "meta_app_secret",
        "meta_login_config_id",
        "meta_redirect_uri",
        "s3_media_bucket",
        "s3_media_region",
        "s3_media_public_base_url",
        "s3_endpoint_url",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        mode="before",
    )
    @classmethod
    def empty_string_as_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @property
    def web_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.web_origins.split(",") if origin.strip()]

    @property
    def clerk_authorized_party_list(self) -> list[str]:
        return [
            party.strip() for party in self.clerk_authorized_parties.split(",") if party.strip()
        ]

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def resolved_meta_redirect_uri(self) -> str:
        if self.meta_redirect_uri:
            return self.meta_redirect_uri
        return f"{str(self.web_base_url).rstrip('/')}/integrations/meta/callback"

    @property
    def resolved_media_public_base_url(self) -> str:
        if self.media_storage_provider == "s3" and self.s3_media_public_base_url:
            return self.s3_media_public_base_url.rstrip("/")
        return self.media_public_base_url.rstrip("/")

    @model_validator(mode="after")
    def validate_portable_runtime(self) -> "Settings":
        if not self.database_url.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError("DATABASE_URL must use PostgreSQL asyncpg or test SQLite aiosqlite")
        if self.environment in {"staging", "production"} and not self.database_url.startswith(
            "postgresql+asyncpg://"
        ):
            raise ValueError("Staging and production require PostgreSQL via asyncpg")
        if not self.redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must use redis or rediss")
        if self.database_pool_size < 1 or self.database_max_overflow < 0:
            raise ValueError("Database pool settings must be non-negative and pool size at least 1")
        for name, value in {
            "APP_BASE_URL": str(self.app_base_url),
            "WEB_BASE_URL": str(self.web_base_url),
            "API_BASE_URL": str(self.api_base_url),
        }.items():
            if self.environment in {"staging", "production"} and urlsplit(value).scheme != "https":
                raise ValueError(f"{name} must use HTTPS outside local/test")
        if self.environment in {"staging", "production"} and not re.fullmatch(
            r"[0-9a-f]{40}", self.release_sha
        ):
            raise ValueError("RELEASE_SHA must be a 40-character lowercase Git SHA")
        return self


def _validate_runtime_security(settings: Settings) -> None:
    if settings.environment in {"local", "test"}:
        return

    if settings.auth_mode == "development":
        raise RuntimeError("Development authentication is forbidden outside local/test")

    key = settings.token_encryption_key
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required outside local/test")
    if key in _INSECURE_TOKEN_ENCRYPTION_KEYS:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY must not use a documented example value")
    if len(key) < _MIN_TOKEN_ENCRYPTION_KEY_LENGTH:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must contain at least "
            f"{_MIN_TOKEN_ENCRYPTION_KEY_LENGTH} characters"
        )

    if settings.media_storage_provider != "s3":
        raise RuntimeError("S3 media storage is required outside local/test")

    required_s3_settings = {
        "S3_MEDIA_BUCKET": settings.s3_media_bucket,
        "S3_MEDIA_REGION": settings.s3_media_region,
        "S3_MEDIA_PUBLIC_BASE_URL": settings.s3_media_public_base_url,
    }
    missing = [name for name, value in required_s3_settings.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required S3 media settings: {', '.join(missing)}")
    media_public_url = settings.s3_media_public_base_url
    if not media_public_url or not media_public_url.startswith("https://"):
        raise RuntimeError("S3_MEDIA_PUBLIC_BASE_URL must use HTTPS outside local/test")
    if settings.s3_endpoint_url and str(settings.s3_endpoint_url).startswith("http://"):
        raise RuntimeError("S3_ENDPOINT_URL must use HTTPS outside local/test")
    if settings.s3_endpoint_url and not (
        settings.aws_access_key_id and settings.aws_secret_access_key
    ):
        raise RuntimeError("S3-compatible endpoints require access key configuration")

    origins = settings.web_origin_list
    if not origins or "*" in origins:
        raise RuntimeError("WEB_ORIGINS must contain an explicit origin allowlist")
    if any(urlsplit(origin).scheme != "https" for origin in origins):
        raise RuntimeError("WEB_ORIGINS must use HTTPS outside local/test")
    hosts = settings.trusted_host_list
    if not hosts or "*" in hosts or any("://" in host or "/" in host for host in hosts):
        raise RuntimeError("TRUSTED_HOSTS must contain explicit hostnames outside local/test")

    if settings.social_provider_meta_enabled:
        required_meta = {
            "META_APP_ID": settings.meta_app_id,
            "META_APP_SECRET": settings.meta_app_secret,
            "META_LOGIN_CONFIG_ID": settings.meta_login_config_id,
        }
        missing_meta = [name for name, value in required_meta.items() if not value]
        if missing_meta:
            raise RuntimeError(f"Missing required Meta settings: {', '.join(missing_meta)}")
        if not settings.resolved_meta_redirect_uri.startswith("https://"):
            raise RuntimeError("Meta redirect URI must use HTTPS outside local/test")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.auth_mode == "clerk" and (
        settings.clerk_jwks_url is None or not settings.clerk_issuer
    ):
        raise RuntimeError("Clerk authentication requires CLERK_JWKS_URL and CLERK_ISSUER")
    _validate_runtime_security(settings)
    return settings
