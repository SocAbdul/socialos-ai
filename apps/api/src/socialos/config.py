from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
AuthMode = Literal["development", "clerk"]

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
    database_url: str = "postgresql+asyncpg://socialos:socialos@localhost:5432/socialos"
    redis_url: str = "redis://localhost:6379/0"
    auth_mode: AuthMode = "development"
    clerk_jwks_url: AnyHttpUrl | None = None
    clerk_issuer: str | None = None
    clerk_audience: str | None = None
    clerk_authorized_parties: str = "http://localhost:3000"
    web_origins: str = "http://localhost:3000"
    token_encryption_key: str | None = None
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    meta_redirect_uri: str = "http://localhost:3000/integrations/meta/callback"
    meta_graph_api_version: str = "v25.0"
    ai_provider: str = "local"
    ai_model: str = "socialos-local-v1"

    @property
    def web_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.web_origins.split(",") if origin.strip()]

    @property
    def clerk_authorized_party_list(self) -> list[str]:
        return [
            party.strip() for party in self.clerk_authorized_parties.split(",") if party.strip()
        ]


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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.auth_mode == "clerk" and (
        settings.clerk_jwks_url is None or not settings.clerk_issuer
    ):
        raise RuntimeError("Clerk authentication requires CLERK_JWKS_URL and CLERK_ISSUER")
    _validate_runtime_security(settings)
    return settings
