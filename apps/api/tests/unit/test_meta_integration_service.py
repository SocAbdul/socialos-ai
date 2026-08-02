from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.infrastructure.database.base import Base
from socialos.infrastructure.database.models import (
    OAuthStateModel,
    PlatformConnectionModel,
    SocialAccountModel,
    WorkspaceModel,
)
from socialos.infrastructure.security.oauth_state import OAuthStateRecord, OAuthStateStore
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.meta.integration import (
    MetaIntegrationService,
    MetaSessionError,
    _candidate_for_intent,
)
from socialos.infrastructure.social.meta.provider import (
    META_REQUIRED_SCOPES,
    MetaAuthorizationExchange,
    MetaPageCandidate,
    MetaSocialProvider,
)


class ExchangeProvider:
    def __init__(self, candidates: list[MetaPageCandidate]) -> None:
        self.candidates = candidates

    async def exchange_authorization(self, code: str) -> MetaAuthorizationExchange:
        return MetaAuthorizationExchange(
            candidates=self.candidates,
            granted_scopes=sorted(META_REQUIRED_SCOPES),
            declined_scopes=[],
            expires_at=None,
            user_access_token=f"user-token-{code}",
        )


class CaptureSession:
    def __init__(self) -> None:
        self.added: object | None = None

    def add(self, model: object) -> None:
        self.added = model


def candidate(
    page_id: str,
    candidate_id: str,
    instagram_id: str | None = "ig-a",
) -> MetaPageCandidate:
    instagram = (
        {
            "id": instagram_id,
            "username": f"kinetic-{instagram_id}",
            "name": "Kinetic Mobiles",
            "account_type": "BUSINESS",
        }
        if instagram_id
        else None
    )
    return MetaPageCandidate(
        candidate_id=candidate_id,
        page_id=page_id,
        page_name=f"Page {page_id}",
        page_access_token=f"page-token-{page_id}",
        page_avatar_url=None,
        page_tasks=["CREATE_CONTENT"],
        instagram=instagram,
    )


def state(workspace_id: UUID, target: UUID) -> OAuthStateRecord:
    return OAuthStateRecord(
        id=uuid4(),
        workspace_id=workspace_id,
        user_id="user-a",
        provider="meta",
        redirect_uri="https://app.test/integrations/meta/callback",
        connection_intent="reconnect",
        channel_nonce="nonce",
        return_to="/integrations",
        target_connection_id=target,
    )


def test_candidate_compatibility_depends_on_intent_tasks_and_account_type() -> None:
    facebook_only = candidate("page-a", "facebook", None)
    assert _candidate_for_intent(facebook_only, "facebook")["compatible"] is True
    assert _candidate_for_intent(facebook_only, "instagram")["compatible"] is False

    no_tasks = candidate("page-a", "no-tasks")
    no_tasks.page_tasks = []
    assert _candidate_for_intent(no_tasks, "facebook")["compatible"] is False

    personal = candidate("page-a", "personal")
    assert personal.instagram is not None
    personal.instagram["account_type"] = "PERSONAL"
    assert _candidate_for_intent(personal, "combined")["compatible"] is False


@pytest.mark.asyncio
async def test_oauth_state_persists_reconnect_target() -> None:
    capture = CaptureSession()
    target = uuid4()
    await OAuthStateStore(cast(AsyncSession, capture)).create(
        workspace_id=uuid4(),
        user_id="user-a",
        provider="meta",
        redirect_uri="https://app.test/integrations/meta/callback",
        connection_intent="reconnect",
        return_to="/integrations",
        target_connection_id=target,
    )
    assert capture.added is not None
    assert cast(OAuthStateModel, capture.added).target_connection_id == target


@pytest_asyncio.fixture
async def database(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'meta.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def seed(
    session: AsyncSession, *, organization_id: str = "org-a"
) -> tuple[WorkspaceModel, PlatformConnectionModel]:
    now = datetime.now(UTC)
    workspace = WorkspaceModel(
        id=uuid4(),
        owner_id="user-a",
        external_organization_id=organization_id,
        name="Kinetic Mobiles",
        created_at=now,
        updated_at=now,
    )
    connection = PlatformConnectionModel(
        id=uuid4(),
        workspace_id=workspace.id,
        provider="meta",
        platform="facebook",
        external_account_id="page-a",
        external_account_name="Page A",
        encrypted_credentials=FernetTokenCipher("test-key").encrypt('{"access_token":"old"}'),
        scopes=sorted(META_REQUIRED_SCOPES),
        granted_scopes=sorted(META_REQUIRED_SCOPES),
        capabilities={"supports_text": True},
        expires_at=None,
        is_valid=True,
        reauth_required=False,
        last_validated_at=now,
        revoked_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add_all([workspace, connection])
    await session.commit()
    return workspace, connection


@pytest.mark.asyncio
async def test_reconnect_accepts_target_page_rejects_another_and_is_idempotent(
    database: async_sessionmaker[AsyncSession],
) -> None:
    async with database() as session:
        workspace, connection = await seed(session)
        actor = Actor("user-a", "org-a", OrganizationRole.ADMIN)
        provider = ExchangeProvider(
            [candidate("page-a", "candidate-a"), candidate("page-b", "candidate-b")]
        )
        service = MetaIntegrationService(
            session, cast(MetaSocialProvider, provider), FernetTokenCipher("test-key")
        )
        public_id = await service.create_session(
            actor=actor, state=state(workspace.id, connection.id), code="one"
        )

        with pytest.raises(MetaSessionError, match="not compatible"):
            await service.select(actor=actor, public_id=public_id, candidate_id="candidate-b")

        first = await service.select(actor=actor, public_id=public_id, candidate_id="candidate-a")
        second = await service.select(actor=actor, public_id=public_id, candidate_id="candidate-a")
        assert first == second
        assert first["connection_id"] == str(connection.id)
        another = await service.create_session(
            actor=actor,
            state=state(workspace.id, connection.id),
            code="concurrent-window",
        )
        third = await service.select(actor=actor, public_id=another, candidate_id="candidate-a")
        assert third["connection_id"] == str(connection.id)
        assert await session.scalar(select(func.count()).select_from(PlatformConnectionModel)) == 1


@pytest.mark.asyncio
async def test_reconnect_hides_target_from_another_workspace(
    database: async_sessionmaker[AsyncSession],
) -> None:
    async with database() as session:
        workspace, _ = await seed(session)
        _, foreign = await seed(session, organization_id="org-b")
        actor = Actor("user-a", "org-a", OrganizationRole.ADMIN)
        service = MetaIntegrationService(
            session,
            cast(MetaSocialProvider, ExchangeProvider([candidate("page-a", "candidate-a")])),
            FernetTokenCipher("test-key"),
        )
        with pytest.raises(MetaSessionError, match="not found"):
            await service.create_session(
                actor=actor, state=state(workspace.id, foreign.id), code="one"
            )


@pytest.mark.asyncio
async def test_reconnect_reconciles_removed_changed_and_restored_instagram(
    database: async_sessionmaker[AsyncSession],
) -> None:
    async with database() as session:
        workspace, connection = await seed(session)
        actor = Actor("user-a", "org-a", OrganizationRole.ADMIN)
        cipher = FernetTokenCipher("test-key")

        async def reconnect(instagram_id: str | None, suffix: str) -> None:
            item = candidate("page-a", f"candidate-{suffix}", instagram_id)
            service = MetaIntegrationService(
                session, cast(MetaSocialProvider, ExchangeProvider([item])), cipher
            )
            public_id = await service.create_session(
                actor=actor, state=state(workspace.id, connection.id), code=suffix
            )
            await service.select(actor=actor, public_id=public_id, candidate_id=item.candidate_id)

        await reconnect("ig-a", "a")
        await reconnect(None, "removed")
        accounts = (
            await session.scalars(
                select(SocialAccountModel).where(SocialAccountModel.platform == "instagram")
            )
        ).all()
        assert [(item.external_account_id, item.active) for item in accounts] == [("ig-a", False)]

        await reconnect("ig-b", "changed")
        accounts = (
            await session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.platform == "instagram")
                .order_by(SocialAccountModel.external_account_id)
            )
        ).all()
        assert [(item.external_account_id, item.active) for item in accounts] == [
            ("ig-a", False),
            ("ig-b", True),
        ]

        await reconnect("ig-a", "restored")
        accounts = (
            await session.scalars(
                select(SocialAccountModel)
                .where(SocialAccountModel.platform == "instagram")
                .order_by(SocialAccountModel.external_account_id)
            )
        ).all()
        assert [(item.external_account_id, item.active) for item in accounts] == [
            ("ig-a", True),
            ("ig-b", False),
        ]
