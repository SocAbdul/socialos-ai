import pytest

from socialos.application.common.auth import OrganizationRole
from socialos.infrastructure.auth.clerk import (
    ClerkTokenVerifier,
    InvalidIdentityTokenError,
)


def verifier() -> ClerkTokenVerifier:
    return ClerkTokenVerifier(
        jwks_url="https://clerk.example/.well-known/jwks.json",
        issuer="https://clerk.example",
        authorized_parties=["https://app.socialos.ai"],
    )


def test_builds_actor_from_version_two_organization_claims() -> None:
    actor = verifier()._actor_from_claims(
        {
            "sub": "user_123",
            "azp": "https://app.socialos.ai",
            "o": {"id": "org_123", "rol": "admin"},
        }
    )

    assert actor.user_id == "user_123"
    assert actor.organization_id == "org_123"
    assert actor.role is OrganizationRole.ADMIN


def test_rejects_untrusted_authorized_party() -> None:
    with pytest.raises(InvalidIdentityTokenError, match="authorized party"):
        verifier()._actor_from_claims(
            {
                "sub": "user_123",
                "azp": "https://attacker.example",
                "o": {"id": "org_123", "rol": "member"},
            }
        )


def test_rejects_missing_authorized_party_when_allowlist_is_configured() -> None:
    with pytest.raises(InvalidIdentityTokenError, match="authorized party"):
        verifier()._actor_from_claims(
            {
                "sub": "user_123",
                "o": {"id": "org_123", "rol": "member"},
            }
        )


def test_requires_active_organization() -> None:
    with pytest.raises(InvalidIdentityTokenError, match="active organization"):
        verifier()._actor_from_claims(
            {
                "sub": "user_123",
                "azp": "https://app.socialos.ai",
            }
        )
