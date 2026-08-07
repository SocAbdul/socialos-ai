from collections.abc import Sequence
from typing import cast
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialProvider
from socialos.application.social.use_cases import BuildMetaAuthorizationUrl
from socialos.config import Settings
from socialos.infrastructure.security.oauth_state import OAuthStateError, validate_oauth_return_to
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta.provider import MetaProviderError, MetaSocialProvider


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


@pytest.mark.asyncio
async def test_refresh_credentials_fails_before_exchanging_a_page_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500, json={})

    settings = Settings(
        meta_app_id="app-id",
        meta_app_secret="secret",  # noqa: S106
        meta_login_config_id="config",
        token_encryption_key="test-key",  # noqa: S106
    )
    cipher = FernetTokenCipher("test-key")
    provider = MetaSocialProvider(
        settings,
        cipher,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    encrypted = cipher.encrypt('{"access_token":"page-token","user_access_token":"user-token"}')

    with pytest.raises(MetaProviderError, match="renewal is not implemented"):
        await provider.refresh_credentials(encrypted)

    assert requests == []


@pytest.mark.asyncio
async def test_connection_validation_checks_permissions_page_tasks_and_instagram() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path.endswith("/me/permissions"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"permission": scope, "status": "granted"}
                        for scope in (
                            "business_management",
                            "pages_show_list",
                            "pages_read_engagement",
                            "pages_manage_posts",
                            "instagram_basic",
                            "instagram_content_publish",
                        )
                    ]
                },
            )
        if request.url.path.endswith("/me/accounts"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "page-a",
                            "name": "Kinetic Mobiles",
                            "access_token": "fresh-page-token",
                            "tasks": ["CREATE_CONTENT"],
                            "instagram_business_account": {
                                "id": "ig-a",
                            },
                        }
                    ]
                },
            )
        if request.url.path.endswith("/ig-a"):
            assert request.url.params["access_token"] == "fresh-page-token"  # noqa: S105
            assert request.url.params["fields"] == (
                "id,username,name,profile_picture_url"
            )
            return httpx.Response(
                200,
                json={
                    "id": "ig-a",
                    "username": "kineticmobiles",
                    "name": "Kinetic Mobiles",
                },
            )
        if request.url.path.endswith("/me"):
            return httpx.Response(200, json={"id": "user-a"})
        return httpx.Response(404, json={"error": {"message": "not found"}})

    settings = Settings(
        meta_app_id="app-id",
        meta_app_secret="secret",  # noqa: S106
        meta_login_config_id="config",
        token_encryption_key="test-key",  # noqa: S106
    )
    cipher = FernetTokenCipher("test-key")
    provider = MetaSocialProvider(
        settings,
        cipher,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    result = await provider.validate_page_authorization(
        cipher.encrypt('{"access_token":"page-token","user_access_token":"user-token"}'),
        "page-a",
    )

    assert result.candidate is not None
    assert result.candidate.page_tasks == ["CREATE_CONTENT"]
    assert result.candidate.instagram is not None
    assert result.candidate.instagram["account_type"] == "PROFESSIONAL"
    assert set(result.granted_scopes) == {
        "business_management",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "instagram_basic",
        "instagram_content_publish",
    }
    assert any(path.endswith("/me") for path in requested)
    assert any(path.endswith("/me/permissions") for path in requested)
    assert any(path.endswith("/me/accounts") for path in requested)
    assert any(path.endswith("/ig-a") for path in requested)
