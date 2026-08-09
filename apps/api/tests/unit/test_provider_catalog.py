from uuid import uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.domain.social import Platform, PlatformConnection, SocialAccount, SocialAccountType
from socialos.infrastructure.providers.errors import (
    CapabilityNotSupported,
    ProviderNotImplemented,
)
from socialos.infrastructure.providers.registry import (
    ProviderNotConfiguredError,
    ProviderStatus,
    build_provider_catalog,
)
from socialos.presentation.api import social as social_api


def test_catalog_declares_verified_meta_and_planned_providers() -> None:
    catalog = build_provider_catalog()

    assert catalog.get("meta").status is ProviderStatus.VERIFIED_IN_DEVELOPMENT
    assert {item.provider: item.status for item in catalog.list()} == {
        "meta": ProviderStatus.VERIFIED_IN_DEVELOPMENT,
        "linkedin": ProviderStatus.PLANNED,
        "youtube": ProviderStatus.PLANNED,
        "tiktok": ProviderStatus.PLANNED,
        "reddit": ProviderStatus.PLANNED,
    }
    assert all(
        not platform.implemented
        for provider in catalog.list()
        if provider.provider != "meta"
        for platform in provider.platforms
    )


def test_meta_capabilities_match_current_socialos_delivery() -> None:
    meta = build_provider_catalog().get("meta")
    facebook, instagram = meta.platforms

    assert facebook.socialos_capabilities.supports_text is True
    assert facebook.socialos_capabilities.supports_single_image is True
    assert facebook.socialos_capabilities.supports_video is False
    assert instagram.socialos_capabilities.supports_text is False
    assert instagram.socialos_capabilities.supports_single_image is True
    assert instagram.socialos_capabilities.requires_public_media_url is True


def test_unknown_and_unsupported_capabilities_fail_explicitly() -> None:
    catalog = build_provider_catalog()

    with pytest.raises(ProviderNotConfiguredError):
        catalog.get("unknown")
    with pytest.raises(CapabilityNotSupported):
        catalog.require_operational("meta", "instagram", "supports_video")


@pytest.mark.parametrize("provider", ["linkedin", "youtube", "tiktok", "reddit"])
def test_planned_provider_cannot_authorize_or_publish(provider: str) -> None:
    catalog = build_provider_catalog(
        linkedin_enabled=True,
        youtube_enabled=True,
        tiktok_enabled=True,
        reddit_enabled=True,
    )

    with pytest.raises(ProviderNotImplemented):
        catalog.require_operational(provider, provider, "authorize")
    with pytest.raises(ProviderNotImplemented):
        catalog.require_operational(provider, provider, "supports_text")


@pytest.mark.asyncio
async def test_catalog_endpoint_reports_connections_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    connection_id = uuid4()
    connection = PlatformConnection(
        workspace_id=workspace_id,
        provider="meta",
        platform=Platform.FACEBOOK,
        external_account_id="page-123",
        external_account_name="Example Page",
        encrypted_credentials="must-not-leak",
        scopes=["must-not-leak"],
        capabilities={},
    )
    connection.id = connection_id
    account = SocialAccount(
        workspace_id=workspace_id,
        platform_connection_id=connection_id,
        platform=Platform.FACEBOOK,
        account_type=SocialAccountType.FACEBOOK_PAGE,
        external_account_id="page-123",
        display_name="Example Page",
        capabilities={"supports_text": True},
    )

    class Connections:
        def __init__(self, _: object) -> None:
            pass

        async def execute(
            self, actor: Actor, requested_workspace_id: object
        ) -> list[PlatformConnection]:
            assert actor.user_id == "user_1"
            assert requested_workspace_id == workspace_id
            return [connection]

    class Accounts:
        def __init__(self, _: object) -> None:
            pass

        async def execute(
            self, actor: Actor, requested_workspace_id: object
        ) -> list[SocialAccount]:
            assert requested_workspace_id == workspace_id
            return [account]

    monkeypatch.setattr(social_api, "ListPlatformConnections", Connections)
    monkeypatch.setattr(social_api, "ListSocialAccounts", Accounts)

    result = await social_api.list_provider_catalog(
        workspace_id,
        Actor("user_1", "org_1", OrganizationRole.ADMIN),
    )
    payload = result.model_dump()

    assert payload["items"][0]["platforms"][0]["connected"] is True
    serialized = str(payload)
    assert "must-not-leak" not in serialized
    assert "encrypted_credentials" not in serialized
