from collections.abc import Mapping
from typing import Any

import jwt
from anyio import to_thread
from jwt import PyJWKClient

from socialos.application.common.auth import Actor, OrganizationRole


class InvalidIdentityTokenError(ValueError):
    """Raised when a Clerk session token is invalid or incomplete."""


class ClerkTokenVerifier:
    def __init__(
        self,
        *,
        jwks_url: str,
        issuer: str,
        authorized_parties: list[str],
        audience: str | None = None,
    ) -> None:
        self._jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        self._issuer = issuer.rstrip("/")
        self._authorized_parties = frozenset(authorized_parties)
        self._audience = audience

    async def verify(self, token: str) -> Actor:
        try:
            signing_key = await to_thread.run_sync(
                self._jwks_client.get_signing_key_from_jwt,
                token,
            )
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"verify_aud": self._audience is not None},
            )
        except jwt.PyJWTError as exc:
            raise InvalidIdentityTokenError("Session token verification failed") from exc

        return self._actor_from_claims(payload)

    def _actor_from_claims(self, claims: Mapping[str, Any]) -> Actor:
        if claims.get("sts") == "pending":
            raise InvalidIdentityTokenError("Organization enrollment is required")

        authorized_party = claims.get("azp")
        if self._authorized_parties and authorized_party not in self._authorized_parties:
            raise InvalidIdentityTokenError("Token authorized party is not allowed")

        user_id = claims.get("sub")
        organization_id, role = self._organization_claims(claims)
        if not isinstance(user_id, str) or not user_id:
            raise InvalidIdentityTokenError("Token is missing its subject")
        if not organization_id:
            raise InvalidIdentityTokenError("An active organization is required")

        try:
            organization_role = OrganizationRole(role)
        except ValueError as exc:
            raise InvalidIdentityTokenError("Organization role is not supported") from exc

        return Actor(
            user_id=user_id,
            organization_id=organization_id,
            role=organization_role,
        )

    @staticmethod
    def _organization_claims(claims: Mapping[str, Any]) -> tuple[str | None, str]:
        organization = claims.get("o")
        if isinstance(organization, Mapping):
            organization_id = organization.get("id")
            compact_role = organization.get("rol")
            role = (
                f"org:{compact_role}"
                if isinstance(compact_role, str) and not compact_role.startswith("org:")
                else compact_role
            )
            return (
                organization_id if isinstance(organization_id, str) else None,
                role if isinstance(role, str) else "",
            )

        organization_id = claims.get("org_id")
        role = claims.get("org_role")
        return (
            organization_id if isinstance(organization_id, str) else None,
            role if isinstance(role, str) else "",
        )
