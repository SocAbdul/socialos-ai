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
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("AUTH_MODE", "clerk")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://clerk.example.test/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_ISSUER", "https://clerk.example.test")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", encryption_key)


def test_rejects_unknown_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "clrek")

    with pytest.raises(ValidationError):
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


def test_accepts_strong_production_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_clerk_environment(monkeypatch, encryption_key="x" * 48)

    settings = get_settings()

    assert settings.environment == "production"
    assert settings.auth_mode == "clerk"
