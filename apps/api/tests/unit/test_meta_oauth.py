from collections.abc import Sequence
from typing import cast
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialProvider
from socialos.application.social.use_cases import BuildMetaAuthorizationUrl
from socialos.config import Settings
from socialos.infrastructure.security.oauth_state import OAuthStateError, validate_oauth_return_to
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta.provider import MetaSocialProvider


class AuthorizationProvider:
    provider_name = "meta"

    def __init__(self) -> None:
        self.received_state: str | None = None
        self.received_scopes: tuple[str, ...] = ()

    def authorize(self, state: str, scopes: Sequence[str]) -> str:
        self.received_state = state
        self.received_scopes = tuple(scopes)
        return "https://facebook.example/dialog/oauth"


@pytest.mark.asyncio
async def test_authorization_uses_persisted_oauth_state_without_prefixing() -> None:
    provider = AuthorizationProvider()
    actor = Actor(
        user_id="user_123",
        organization_id="org_123",
        role=OrganizationRole.ADMIN,
    )
    state = "opaque-random-state"

    url = await BuildMetaAuthorizationUrl(cast(SocialProvider, provider)).execute(
        actor,
        uuid4(),
        state,
    )

    assert url == "https://facebook.example/dialog/oauth"
    assert provider.received_state == state
    assert "pages_manage_posts" in provider.received_scopes


def test_meta_login_for_business_url_uses_config_id_without_scope_override() -> None:
    settings = Settings(
        meta_app_id="app-id",
        meta_app_secret="app-secret",  # noqa: S106 - inert unit-test value
        meta_login_config_id="config-from-environment",
        token_encryption_key="test-key",  # noqa: S106 - inert unit-test value
    )
    url = MetaSocialProvider(settings, FernetTokenCipher("test-key")).authorize(
        "opaque-state", ["must-not-be-serialized"]
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.hostname == "www.facebook.com"
    assert query["config_id"] == ["config-from-environment"]
    assert query["state"] == ["opaque-state"]
    assert query["response_type"] == ["code"]
    assert "scope" not in query
    assert "override_default_response_type" not in query
    assert "app-secret" not in url


@pytest.mark.parametrize(
    "unsafe",
    ["//example.com", "https://example.com", "/integrations\\evil", "/", "/integrations?next=/"],
)
def test_oauth_return_path_rejects_everything_outside_exact_allowlist(unsafe: str) -> None:
    with pytest.raises(OAuthStateError, match="not allowed"):
        validate_oauth_return_to(unsafe)


def test_oauth_return_path_accepts_integrations_only() -> None:
    assert validate_oauth_return_to("/integrations") == "/integrations"
