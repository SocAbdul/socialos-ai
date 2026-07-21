from functools import lru_cache
from typing import Annotated

from fastapi import Header, HTTPException, status

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.config import get_settings
from socialos.infrastructure.auth.clerk import (
    ClerkTokenVerifier,
    InvalidIdentityTokenError,
)


@lru_cache
def get_clerk_verifier() -> ClerkTokenVerifier:
    settings = get_settings()
    if settings.clerk_jwks_url is None or not settings.clerk_issuer:
        raise RuntimeError("Clerk authentication is not configured")
    return ClerkTokenVerifier(
        jwks_url=str(settings.clerk_jwks_url),
        issuer=settings.clerk_issuer,
        audience=settings.clerk_audience,
        authorized_parties=settings.clerk_authorized_party_list,
    )


async def get_actor(
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_organization_id: Annotated[str | None, Header()] = None,
    x_organization_role: Annotated[str | None, Header()] = None,
) -> Actor:
    settings = get_settings()
    if settings.auth_mode == "development":
        return _development_actor(x_user_id, x_organization_id, x_organization_role)

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A bearer session token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await get_clerk_verifier().verify(authorization.removeprefix("Bearer ").strip())
    except InvalidIdentityTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _development_actor(
    user_id: str | None,
    organization_id: str | None,
    organization_role: str | None,
) -> Actor:
    if not user_id or not organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development identity headers are required",
        )
    try:
        role = OrganizationRole(organization_role or OrganizationRole.ADMIN)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development organization role is invalid",
        ) from exc
    return Actor(user_id=user_id, organization_id=organization_id, role=role)
