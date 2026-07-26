from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from socialos.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def configure_clerk_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    environment: str = "production",
    encryption_key: str,
    configure_s3: bool = True,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("AUTH_MODE", "clerk")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://clerk.example.test/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_ISSUER", "https://clerk.example.test")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", encryption_key)
    if configure_s3:
        monkeypatch.setenv("MEDIA_STORAGE_PROVIDER", "s3")
        monkeypatch.setenv("S3_MEDIA_BUCKET", "socialos-media-test")
        monkeypatch.setenv("S3_MEDIA_REGION", "eu-west-2")
        monkeypatch.setenv("S3_MEDIA_PUBLIC_BASE_URL", "https://media.example.test")


def test_rejects_unknown_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "clrek")

    with pytest.raises(ValidationError):
        get_settings()


def test_accepts_empty_optional_clerk_values_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("AUTH_MODE", "development")
    monkeypatch.setenv("CLERK_JWKS_URL", "")
    monkeypatch.setenv("CLERK_ISSUER", "")

    settings = get_settings()

    assert settings.auth_mode == "development"
    assert settings.clerk_jwks_url is None
    assert settings.clerk_issuer is None


def test_rejects_empty_clerk_values_when_clerk_auth_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("AUTH_MODE", "clerk")
    monkeypatch.setenv("CLERK_JWKS_URL", "")
    monkeypatch.setenv("CLERK_ISSUER", "")

    with pytest.raises(RuntimeError, match="Clerk authentication requires"):
        get_settings()


def test_rejects_development_authentication_in_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("AUTH_MODE", "development")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "x" * 48)

    with pytest.raises(RuntimeError, match="Development authentication"):
        get_settings()


def test_rejects_documented_example_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_clerk_environment(
        monkeypatch,
        encryption_key="replace-with-a-long-random-secret",
    )

    with pytest.raises(RuntimeError, match="documented example"):
        get_settings()


def test_rejects_short_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_clerk_environment(monkeypatch, encryption_key="too-short")

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        get_settings()


def test_requires_s3_media_storage_outside_local_test(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_clerk_environment(
        monkeypatch,
        encryption_key="x" * 48,
        configure_s3=False,
    )

    with pytest.raises(RuntimeError, match="S3 media storage"):
        get_settings()


def test_accepts_strong_production_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_clerk_environment(monkeypatch, encryption_key="x" * 48)

    settings = get_settings()

    assert settings.environment == "production"
    assert settings.auth_mode == "clerk"
    assert settings.media_storage_provider == "s3"


def test_production_s3_configuration_does_not_require_static_aws_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_clerk_environment(monkeypatch, encryption_key="x" * 48)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    settings = get_settings()

    assert settings.aws_access_key_id is None
    assert settings.aws_secret_access_key is None
