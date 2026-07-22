from collections.abc import Sequence
from typing import cast
from uuid import uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialProvider
from socialos.application.social.use_cases import BuildMetaAuthorizationUrl


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
