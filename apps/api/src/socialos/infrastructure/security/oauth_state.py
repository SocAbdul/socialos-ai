import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from socialos.infrastructure.database.models import OAuthStateModel


class OAuthStateError(ValueError):
    """Raised when an OAuth state is invalid, expired, or already used."""


@dataclass(frozen=True, slots=True)
class OAuthStateRecord:
    id: UUID
    workspace_id: UUID
    user_id: str
    provider: str
    redirect_uri: str
    connection_intent: str
    channel_nonce: str
    return_to: str


@dataclass(frozen=True, slots=True)
class OAuthStateCreation:
    state: str
    channel_nonce: str


ALLOWED_OAUTH_RETURN_PATHS = frozenset({"/integrations"})


def validate_oauth_return_to(return_to: str) -> str:
    if return_to not in ALLOWED_OAUTH_RETURN_PATHS:
        raise OAuthStateError("OAuth return path is not allowed")
    return return_to


class OAuthStateStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workspace_id: UUID,
        user_id: str,
        provider: str,
        redirect_uri: str,
        connection_intent: str,
        return_to: str,
        ttl: timedelta = timedelta(minutes=10),
    ) -> OAuthStateCreation:
        state = secrets.token_urlsafe(32)
        channel_nonce = secrets.token_urlsafe(32)
        safe_return_to = validate_oauth_return_to(return_to)
        now = datetime.now(UTC)
        self._session.add(
            OAuthStateModel(
                workspace_id=workspace_id,
                user_id=user_id,
                provider=provider,
                redirect_uri=redirect_uri,
                connection_intent=connection_intent,
                channel_nonce=channel_nonce,
                return_to=safe_return_to,
                state_hash=_hash_state(state),
                expires_at=now + ttl,
                created_at=now,
            )
        )
        return OAuthStateCreation(state=state, channel_nonce=channel_nonce)

    async def consume(
        self,
        *,
        state: str,
        user_id: str,
        provider: str,
        redirect_uri: str,
    ) -> OAuthStateRecord:
        model = await self._session.scalar(
            select(OAuthStateModel)
            .where(OAuthStateModel.state_hash == _hash_state(state))
            .with_for_update()
        )
        now = datetime.now(UTC)
        if model is None:
            raise OAuthStateError("OAuth state is invalid")
        if model.used_at is not None:
            raise OAuthStateError("OAuth state has already been used")
        if model.expires_at <= now:
            raise OAuthStateError("OAuth state has expired")
        if (
            model.user_id != user_id
            or model.provider != provider
            or model.redirect_uri != redirect_uri
        ):
            raise OAuthStateError("OAuth state context does not match")
        model.used_at = now
        return OAuthStateRecord(
            id=model.id,
            workspace_id=model.workspace_id,
            user_id=model.user_id,
            provider=model.provider,
            redirect_uri=model.redirect_uri,
            connection_intent=model.connection_intent,
            channel_nonce=model.channel_nonce,
            return_to=model.return_to,
        )


def _hash_state(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()
