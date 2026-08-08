import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
from cryptography.fernet import InvalidToken
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from socialos.application.common.auth import Actor
from socialos.domain.social import Platform
from socialos.infrastructure.database.models import (
    ConnectionAuditEventModel,
    MetaOAuthSessionModel,
    PlatformConnectionModel,
    SocialAccountModel,
    WorkspaceModel,
)
from socialos.infrastructure.providers.registry import (
    FACEBOOK_CAPABILITIES,
    INSTAGRAM_CAPABILITIES,
)
from socialos.infrastructure.security.oauth_state import OAuthStateRecord
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta.provider import (
    META_REQUIRED_SCOPES,
    MetaPermissionError,
    MetaProviderError,
    MetaSocialProvider,
)

SESSION_TTL = timedelta(minutes=10)
META_PUBLISH_TASKS = frozenset({"CREATE_CONTENT", "MANAGE"})
INSTAGRAM_ACCOUNT_TYPES = frozenset({"BUSINESS", "CREATOR", "MEDIA_CREATOR", "PROFESSIONAL"})


class MetaSessionError(ValueError):
    """Raised when a temporary Meta OAuth session cannot be used safely."""


class MetaValidationTemporaryError(RuntimeError):
    """Raised when Meta validation can be retried without changing known-good state."""

    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


class MetaIntegrationService:
    def __init__(
        self,
        session: AsyncSession,
        provider: MetaSocialProvider,
        cipher: FernetTokenCipher,
    ) -> None:
        self._session = session
        self._provider = provider
        self._cipher = cipher

    async def create_session(
        self,
        *,
        actor: Actor,
        state: OAuthStateRecord,
        code: str,
    ) -> str:
        await self._require_workspace(actor, state.workspace_id)
        exchange = await self._provider.exchange_authorization(code)
        missing = sorted(META_REQUIRED_SCOPES.difference(exchange.granted_scopes))
        if missing:
            await self._audit(
                workspace_id=state.workspace_id,
                actor_id=actor.user_id,
                event_type="permission_changed",
                safe_metadata={"missing_permissions": missing},
            )
            await self._session.commit()
            raise MetaPermissionError(
                "Meta did not grant every permission required for Facebook and Instagram publishing"
            )
        target: PlatformConnectionModel | None = None
        compatibility_intent = state.connection_intent
        candidates = exchange.candidates
        if state.connection_intent == "reconnect":
            if state.target_connection_id is None:
                raise MetaSessionError("Reconnect target is missing")
            target = await self._connection_for_actor(
                actor, state.target_connection_id, for_update=False
            )
            if target.workspace_id != state.workspace_id:
                raise MetaSessionError("Meta connection was not found")
            candidates = [
                candidate
                for candidate in candidates
                if candidate.page_id == target.external_account_id
            ]
            compatibility_intent = "facebook"
        if not candidates:
            raise MetaSessionError("Meta did not return a compatible Facebook Page")

        public_id = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        model = MetaOAuthSessionModel(
            id=uuid4(),
            session_hash=_hash(public_id),
            oauth_state_id=state.id,
            user_id=actor.user_id,
            workspace_id=state.workspace_id,
            provider="meta",
            connection_intent=state.connection_intent,
            channel_nonce=state.channel_nonce,
            return_to=state.return_to,
            encrypted_temporary_token=self._cipher.encrypt(
                json.dumps(
                    {
                        "candidates": [candidate.secret_dict() for candidate in candidates],
                        "user_access_token": exchange.user_access_token,
                        "expires_at": (
                            exchange.expires_at.isoformat() if exchange.expires_at else None
                        ),
                    }
                )
            ),
            candidates=[
                _candidate_for_intent(candidate, compatibility_intent) for candidate in candidates
            ],
            required_scopes=sorted(META_REQUIRED_SCOPES),
            granted_scopes=exchange.granted_scopes,
            declined_scopes=exchange.declined_scopes,
            expires_at=now + SESSION_TTL,
            completed_at=None,
            result=None,
            target_connection_id=target.id if target else None,
            created_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        return public_id

    async def ensure_connection_access(self, *, actor: Actor, connection_id: UUID) -> None:
        await self._connection_for_actor(actor, connection_id, for_update=False)

    async def ensure_workspace_access(self, *, actor: Actor, workspace_id: UUID) -> None:
        await self._require_workspace(actor, workspace_id)

    async def status(self, *, actor: Actor, workspace_id: UUID) -> dict[str, object]:
        await self._require_workspace(actor, workspace_id)
        connections = (
            await self._session.scalars(
                select(PlatformConnectionModel).where(
                    PlatformConnectionModel.workspace_id == workspace_id,
                    PlatformConnectionModel.provider == "meta",
                )
            )
        ).all()
        connection_ids = [item.id for item in connections]
        accounts = (
            (
                await self._session.scalars(
                    select(SocialAccountModel).where(
                        SocialAccountModel.platform_connection_id.in_(connection_ids)
                    )
                )
            ).all()
            if connection_ids
            else []
        )
        return {
            "connections": [
                {
                    "id": str(item.id),
                    "page_name": item.external_account_name,
                    "masked_page_id": _mask_identifier(item.external_account_id),
                    "state": _connection_state(item),
                    "last_validated_at": (
                        item.last_validated_at.isoformat() if item.last_validated_at else None
                    ),
                }
                for item in connections
            ],
            "accounts": [
                {
                    "id": str(item.id),
                    "connection_id": str(item.platform_connection_id),
                    "platform": item.platform,
                    "display_name": item.display_name,
                    "username": item.username,
                    "masked_external_id": _mask_identifier(item.external_account_id),
                    "active": item.active,
                    "avatar_url": item.safe_metadata.get("avatar_url"),
                    "account_type": item.safe_metadata.get("account_type"),
                    "parent_page_name": item.safe_metadata.get("parent_page_name"),
                }
                for item in accounts
            ],
        }

    async def details(self, *, actor: Actor, connection_id: UUID) -> dict[str, object]:
        connection = await self._connection_for_actor(actor, connection_id, for_update=False)
        return {
            "id": str(connection.id),
            "required_scopes": connection.scopes,
            "granted_scopes": connection.granted_scopes,
            "missing_scopes": sorted(META_REQUIRED_SCOPES.difference(connection.granted_scopes)),
            "expires_at": connection.expires_at.isoformat() if connection.expires_at else None,
            "is_valid": connection.is_valid,
            "reauth_required": connection.reauth_required,
            "revoked_at": connection.revoked_at.isoformat() if connection.revoked_at else None,
            "last_validated_at": (
                connection.last_validated_at.isoformat() if connection.last_validated_at else None
            ),
        }

    async def get_session(
        self,
        *,
        actor: Actor,
        public_id: str,
        for_update: bool = False,
        allow_completed: bool = False,
    ) -> MetaOAuthSessionModel:
        statement = (
            select(MetaOAuthSessionModel)
            .join(WorkspaceModel, WorkspaceModel.id == MetaOAuthSessionModel.workspace_id)
            .where(
                MetaOAuthSessionModel.session_hash == _hash(public_id),
                MetaOAuthSessionModel.user_id == actor.user_id,
                MetaOAuthSessionModel.provider == "meta",
                WorkspaceModel.external_organization_id == actor.organization_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        if model is None:
            raise MetaSessionError("Meta connection session was not found")
        now = datetime.now(UTC)
        if _as_utc(model.expires_at) <= now:
            raise MetaSessionError("Meta connection session has expired")
        if model.completed_at is not None and not allow_completed:
            raise MetaSessionError("Meta connection session was not found")
        return model

    async def select(
        self,
        *,
        actor: Actor,
        public_id: str,
        candidate_id: str,
    ) -> dict[str, object]:
        model = await self.get_session(
            actor=actor, public_id=public_id, for_update=True, allow_completed=True
        )
        if model.completed_at is not None:
            return cast(dict[str, object], model.result or {})
        safe_candidate = next(
            (item for item in model.candidates if item.get("candidate_id") == candidate_id), None
        )
        if safe_candidate is None or not safe_candidate.get("compatible"):
            raise MetaSessionError("The selected Meta account is not compatible")
        secret_payload = cast(
            dict[str, Any], json.loads(self._cipher.decrypt(model.encrypted_temporary_token))
        )
        candidates = cast(list[dict[str, Any]], secret_payload.get("candidates", []))
        candidate = next(
            (item for item in candidates if item.get("candidate_id") == candidate_id), None
        )
        if candidate is None:
            raise MetaSessionError("The selected Meta account is no longer available")
        if model.connection_intent == "reconnect":
            if model.target_connection_id is None:
                raise MetaSessionError("Reconnect target is missing")
            target = await self._connection_for_actor(
                actor, model.target_connection_id, for_update=True
            )
            if target.workspace_id != model.workspace_id or target.external_account_id != str(
                candidate["page_id"]
            ):
                raise MetaSessionError("The selected Page does not match the reconnect target")
        connection = await self._upsert_connection(model, candidate)
        account_ids = await self._reconcile_accounts(model, connection, candidate)
        event_type = "reconnect" if model.connection_intent == "reconnect" else "connect"
        await self._audit(
            workspace_id=model.workspace_id,
            actor_id=actor.user_id,
            event_type=event_type,
            platform_connection_id=connection.id,
            safe_metadata={"connection_intent": model.connection_intent},
        )
        model.completed_at = datetime.now(UTC)
        model.encrypted_temporary_token = self._cipher.encrypt(json.dumps({"completed": True}))
        model.result = {
            "connection_id": str(connection.id),
            "account_ids": [str(account_id) for account_id in account_ids],
            "return_to": model.return_to,
            "connection_intent": model.connection_intent,
            "channel_nonce": model.channel_nonce,
        }
        await self._session.commit()
        return model.result

    async def disconnect(self, *, actor: Actor, connection_id: UUID) -> None:
        connection = await self._connection_for_actor(actor, connection_id, for_update=True)
        now = datetime.now(UTC)
        connection.encrypted_credentials = self._cipher.encrypt(json.dumps({"disconnected": True}))
        connection.is_valid = False
        connection.reauth_required = True
        connection.revoked_at = now
        connection.updated_at = now
        accounts = (
            await self._session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.platform_connection_id == connection.id)
                .with_for_update()
            )
        ).all()
        for account in accounts:
            account.active = False
            account.selected = False
            account.updated_at = now
        await self._audit(
            workspace_id=connection.workspace_id,
            actor_id=actor.user_id,
            event_type="disconnect",
            platform_connection_id=connection.id,
            safe_metadata={"authorization_revoked_at_meta": False},
        )
        await self._session.commit()

    async def validate(self, *, actor: Actor, connection_id: UUID) -> bool:
        connection = await self._connection_for_actor(actor, connection_id, for_update=True)
        now = datetime.now(UTC)
        previous_scopes = set(connection.granted_scopes)
        try:
            validation = await self._provider.validate_page_authorization(
                connection.encrypted_credentials, connection.external_account_id
            )
            candidate = validation.candidate
            permissions_ok = META_REQUIRED_SCOPES.issubset(validation.granted_scopes)
            tasks_ok = bool(candidate and META_PUBLISH_TASKS.intersection(candidate.page_tasks))
            valid = bool(candidate and permissions_ok and tasks_ok)
            if candidate and valid:
                connection.granted_scopes = validation.granted_scopes
                credentials = cast(
                    dict[str, str],
                    json.loads(self._cipher.decrypt(connection.encrypted_credentials)),
                )
                credentials["access_token"] = candidate.page_access_token
                connection.encrypted_credentials = self._cipher.encrypt(json.dumps(credentials))
                await self._reconcile_accounts(
                    SimpleNamespace(
                        workspace_id=connection.workspace_id,
                        user_id=actor.user_id,
                    ),
                    connection,
                    candidate.secret_dict(),
                )
            else:
                connection.granted_scopes = validation.granted_scopes
                await self._deactivate_all_accounts(
                    connection=connection, actor_id=actor.user_id, now=now
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            await self._record_temporary_validation_failure(
                connection=connection, actor_id=actor.user_id, reason="network"
            )
            raise MetaValidationTemporaryError(
                "Meta validation is temporarily unavailable", status_code=503
            ) from exc
        except MetaProviderError as exc:
            if exc.retryable:
                await self._record_temporary_validation_failure(
                    connection=connection,
                    actor_id=actor.user_id,
                    reason="meta_retryable",
                    error_code=exc.error_code,
                )
                raise MetaValidationTemporaryError(
                    "Meta validation is temporarily unavailable", status_code=502
                ) from exc
            if exc.error_code != "190":
                await self._session.rollback()
                raise
            valid = False
            connection.granted_scopes = []
            await self._deactivate_all_accounts(
                connection=connection, actor_id=actor.user_id, now=now
            )
        except (SQLAlchemyError, InvalidToken, json.JSONDecodeError, KeyError, TypeError):
            await self._session.rollback()
            raise
        connection.last_validated_at = now
        connection.is_valid = valid
        connection.reauth_required = not valid
        connection.updated_at = now
        if previous_scopes != set(connection.granted_scopes):
            await self._audit(
                workspace_id=connection.workspace_id,
                actor_id=actor.user_id,
                event_type="permission_changed",
                platform_connection_id=connection.id,
                safe_metadata={
                    "missing_permissions": sorted(
                        META_REQUIRED_SCOPES.difference(connection.granted_scopes)
                    )
                },
            )
        if not valid:
            await self._audit(
                workspace_id=connection.workspace_id,
                actor_id=actor.user_id,
                event_type="validation_failed",
                platform_connection_id=connection.id,
                safe_metadata={},
            )
            await self._audit(
                workspace_id=connection.workspace_id,
                actor_id=actor.user_id,
                event_type="reauthorization_required",
                platform_connection_id=connection.id,
                safe_metadata={},
            )
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise
        return valid

    async def _record_temporary_validation_failure(
        self,
        *,
        connection: PlatformConnectionModel,
        actor_id: str,
        reason: str,
        error_code: str | None = None,
    ) -> None:
        safe_metadata: dict[str, object] = {"reason": reason, "retryable": True}
        if error_code is not None:
            safe_metadata["error_code"] = error_code
        await self._audit(
            workspace_id=connection.workspace_id,
            actor_id=actor_id,
            event_type="validation_retryable_failed",
            platform_connection_id=connection.id,
            safe_metadata=safe_metadata,
        )
        try:
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def _deactivate_all_accounts(
        self,
        *,
        connection: PlatformConnectionModel,
        actor_id: str,
        now: datetime,
    ) -> None:
        accounts = (
            await self._session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.platform_connection_id == connection.id)
                .with_for_update()
            )
        ).all()
        for account in accounts:
            if not account.active:
                continue
            account.active = False
            account.selected = False
            account.last_validated_at = now
            account.updated_at = now
            await self._audit(
                workspace_id=connection.workspace_id,
                actor_id=actor_id,
                event_type="account_unlinked",
                platform_connection_id=connection.id,
                safe_metadata={"platform": account.platform},
            )

    async def _upsert_connection(
        self,
        oauth_session: MetaOAuthSessionModel,
        candidate: dict[str, Any],
    ) -> PlatformConnectionModel:
        page_id = str(candidate["page_id"])
        if oauth_session.connection_intent == "reconnect":
            if oauth_session.target_connection_id is None:
                raise MetaSessionError("Reconnect target is missing")
            connection = await self._session.scalar(
                select(PlatformConnectionModel)
                .where(
                    PlatformConnectionModel.id == oauth_session.target_connection_id,
                    PlatformConnectionModel.workspace_id == oauth_session.workspace_id,
                    PlatformConnectionModel.provider == "meta",
                    PlatformConnectionModel.external_account_id == page_id,
                )
                .with_for_update()
            )
            if connection is None:
                raise MetaSessionError("Meta connection was not found")
        else:
            connection = await self._session.scalar(
                select(PlatformConnectionModel)
                .where(
                    PlatformConnectionModel.workspace_id == oauth_session.workspace_id,
                    PlatformConnectionModel.provider == "meta",
                    PlatformConnectionModel.external_account_id == page_id,
                )
                .with_for_update()
            )
        now = datetime.now(UTC)
        oauth_payload = cast(
            dict[str, Any],
            json.loads(self._cipher.decrypt(oauth_session.encrypted_temporary_token)),
        )
        encrypted = self._cipher.encrypt(
            json.dumps(
                {
                    "access_token": str(candidate["page_access_token"]),
                    "user_access_token": str(oauth_payload["user_access_token"]),
                }
            )
        )
        expires_raw = oauth_payload.get("expires_at")
        expires_at = datetime.fromisoformat(str(expires_raw)) if expires_raw else None
        if connection is None:
            connection = PlatformConnectionModel(
                id=uuid4(),
                workspace_id=oauth_session.workspace_id,
                provider="meta",
                platform=Platform.FACEBOOK.value,
                external_account_id=page_id,
                external_account_name=str(candidate["page_name"]),
                encrypted_credentials=encrypted,
                scopes=oauth_session.required_scopes,
                granted_scopes=oauth_session.granted_scopes,
                capabilities=FACEBOOK_CAPABILITIES.as_dict(),
                expires_at=expires_at,
                is_valid=True,
                reauth_required=False,
                revoked_at=None,
                last_validated_at=now,
                created_at=now,
                updated_at=now,
            )
            self._session.add(connection)
        else:
            connection.external_account_name = str(candidate["page_name"])
            connection.encrypted_credentials = encrypted
            connection.scopes = oauth_session.required_scopes
            connection.granted_scopes = oauth_session.granted_scopes
            connection.capabilities = FACEBOOK_CAPABILITIES.as_dict()
            connection.expires_at = expires_at
            connection.is_valid = True
            connection.reauth_required = False
            connection.revoked_at = None
            connection.last_validated_at = now
            connection.updated_at = now
        return connection

    async def _reconcile_accounts(
        self,
        oauth_session: Any,
        connection: PlatformConnectionModel,
        candidate: dict[str, Any],
    ) -> list[UUID]:
        now = datetime.now(UTC)
        existing = (
            await self._session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.platform_connection_id == connection.id)
                .with_for_update()
            )
        ).all()
        active_keys: set[tuple[str, str]] = set()
        page = await self._upsert_account(
            workspace_id=oauth_session.workspace_id,
            connection_id=connection.id,
            platform="facebook",
            account_type="facebook_page",
            external_id=str(candidate["page_id"]),
            display_name=str(candidate["page_name"]),
            username=None,
            capabilities=FACEBOOK_CAPABILITIES.as_dict(),
            safe_metadata={
                "avatar_url": candidate.get("page_avatar_url"),
                "tasks": candidate.get("page_tasks", []),
            },
            parent_account_id=None,
            now=now,
            actor_id=oauth_session.user_id,
        )
        ids = [page.id]
        active_keys.add(("facebook", str(candidate["page_id"])))
        instagram = candidate.get("instagram")
        if (
            isinstance(instagram, dict)
            and instagram.get("id")
            and str(instagram.get("account_type", "")).upper() in INSTAGRAM_ACCOUNT_TYPES
        ):
            account = await self._upsert_account(
                workspace_id=oauth_session.workspace_id,
                connection_id=connection.id,
                platform="instagram",
                account_type="instagram_business",
                external_id=str(instagram["id"]),
                display_name=str(
                    instagram.get("name") or instagram.get("username") or instagram["id"]
                ),
                username=str(instagram["username"]) if instagram.get("username") else None,
                capabilities=INSTAGRAM_CAPABILITIES.as_dict(),
                safe_metadata={
                    "avatar_url": instagram.get("profile_picture_url"),
                    "account_type": instagram.get("account_type") or "PROFESSIONAL",
                    "parent_page_name": candidate["page_name"],
                },
                parent_account_id=page.id,
                now=now,
                actor_id=oauth_session.user_id,
            )
            ids.append(account.id)
            active_keys.add(("instagram", str(instagram["id"])))
        for account in existing:
            if (
                account.platform,
                account.external_account_id,
            ) not in active_keys and account.active:
                account.active = False
                account.selected = False
                account.updated_at = now
                await self._audit(
                    workspace_id=oauth_session.workspace_id,
                    actor_id=oauth_session.user_id,
                    event_type="account_unlinked",
                    platform_connection_id=connection.id,
                    safe_metadata={"platform": account.platform},
                )
        return ids

    async def _upsert_account(
        self,
        *,
        workspace_id: UUID,
        connection_id: UUID,
        platform: str,
        account_type: str,
        external_id: str,
        display_name: str,
        username: str | None,
        capabilities: dict[str, object],
        safe_metadata: dict[str, object],
        parent_account_id: UUID | None,
        now: datetime,
        actor_id: str,
    ) -> SocialAccountModel:
        account = await self._session.scalar(
            select(SocialAccountModel)
            .where(
                SocialAccountModel.platform_connection_id == connection_id,
                SocialAccountModel.platform == platform,
                SocialAccountModel.external_account_id == external_id,
            )
            .with_for_update()
        )
        if account is None:
            account = SocialAccountModel(
                id=uuid4(),
                workspace_id=workspace_id,
                platform_connection_id=connection_id,
                parent_account_id=parent_account_id,
                platform=platform,
                account_type=account_type,
                external_account_id=external_id,
                display_name=display_name,
                username=username,
                capabilities=capabilities,
                selected=True,
                active=True,
                safe_metadata=safe_metadata,
                last_validated_at=now,
                created_at=now,
                updated_at=now,
            )
            self._session.add(account)
        else:
            was_inactive = not account.active
            account.parent_account_id = parent_account_id
            account.display_name = display_name
            account.username = username
            account.capabilities = capabilities
            account.safe_metadata = safe_metadata
            account.selected = True
            account.active = True
            account.last_validated_at = now
            account.updated_at = now
            if was_inactive:
                await self._audit(
                    workspace_id=workspace_id,
                    actor_id=actor_id,
                    event_type="account_reactivated",
                    platform_connection_id=connection_id,
                    safe_metadata={"platform": platform},
                )
        return account

    async def _connection_for_actor(
        self, actor: Actor, connection_id: UUID, *, for_update: bool
    ) -> PlatformConnectionModel:
        statement = (
            select(PlatformConnectionModel)
            .join(WorkspaceModel, WorkspaceModel.id == PlatformConnectionModel.workspace_id)
            .where(
                PlatformConnectionModel.id == connection_id,
                PlatformConnectionModel.provider == "meta",
                WorkspaceModel.external_organization_id == actor.organization_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()
        connection = await self._session.scalar(statement)
        if connection is None:
            raise MetaSessionError("Meta connection was not found")
        return connection

    async def _require_workspace(self, actor: Actor, workspace_id: UUID) -> None:
        workspace = await self._session.scalar(
            select(WorkspaceModel).where(
                WorkspaceModel.id == workspace_id,
                WorkspaceModel.external_organization_id == actor.organization_id,
            )
        )
        if workspace is None:
            raise MetaSessionError("Workspace was not found")

    async def _audit(
        self,
        *,
        workspace_id: UUID,
        actor_id: str,
        event_type: str,
        safe_metadata: dict[str, object],
        platform_connection_id: UUID | None = None,
    ) -> None:
        self._session.add(
            ConnectionAuditEventModel(
                id=uuid4(),
                workspace_id=workspace_id,
                platform_connection_id=platform_connection_id,
                actor_id=actor_id,
                event_type=event_type,
                safe_metadata=safe_metadata,
                created_at=datetime.now(UTC),
            )
        )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _candidate_for_intent(candidate: Any, intent: str) -> dict[str, object]:
    safe = candidate.safe_dict()
    tasks_ok = bool(META_PUBLISH_TASKS.intersection(candidate.page_tasks))
    instagram = candidate.instagram
    instagram_ok = bool(
        instagram
        and instagram.get("id")
        and str(instagram.get("account_type", "")).upper() in INSTAGRAM_ACCOUNT_TYPES
    )
    compatible = tasks_ok and (intent == "facebook" or instagram_ok)
    if not tasks_ok:
        message = "This Page does not grant content publishing access."
    elif intent != "facebook" and not instagram_ok:
        message = "A compatible Business or Creator Instagram account is required."
    elif instagram_ok:
        message = "Facebook Page and professional Instagram account are available."
    else:
        message = "Facebook Page is available."
    return {**safe, "compatible": compatible, "compatibility_message": message}


def _connection_locally_valid(connection: PlatformConnectionModel) -> bool:
    return bool(
        connection.is_valid
        and not connection.reauth_required
        and connection.revoked_at is None
        and (connection.expires_at is None or _as_utc(connection.expires_at) > datetime.now(UTC))
        and META_REQUIRED_SCOPES.issubset(connection.granted_scopes)
    )


def _connection_state(connection: PlatformConnectionModel) -> str:
    if connection.revoked_at is not None:
        return "disconnected"
    if connection.reauth_required:
        return "reauth_required"
    if connection.expires_at is not None and _as_utc(connection.expires_at) <= datetime.now(UTC):
        return "expired"
    if not META_REQUIRED_SCOPES.issubset(connection.granted_scopes):
        return "permission_missing"
    return "connected" if connection.is_valid else "error"


def _mask_identifier(value: str) -> str:
    return f"••••••{value[-4:]}" if len(value) > 4 else "••••"
