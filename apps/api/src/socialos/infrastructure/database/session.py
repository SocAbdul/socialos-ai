from collections.abc import AsyncIterator
from typing import Self

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from socialos.application.posts.ports import PostRepository
from socialos.application.social.ports import (
    AIGenerationRepository,
    BrandProfileRepository,
    CampaignRepository,
    ContentItemRepository,
    MediaAssetRepository,
    PlatformConnectionRepository,
    PublicationAttemptRepository,
    PublicationRepository,
    SocialAccountRepository,
    WorkspaceRepository,
)
from socialos.config import get_settings
from socialos.infrastructure.database.repositories import (
    SqlAlchemyAIGenerationRepository,
    SqlAlchemyBrandProfileRepository,
    SqlAlchemyCampaignRepository,
    SqlAlchemyContentItemRepository,
    SqlAlchemyMediaAssetRepository,
    SqlAlchemyPlatformConnectionRepository,
    SqlAlchemyPostRepository,
    SqlAlchemyPublicationAttemptRepository,
    SqlAlchemyPublicationRepository,
    SqlAlchemySocialAccountRepository,
    SqlAlchemyWorkspaceRepository,
)

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyUnitOfWork:
    def __init__(self, factory: async_sessionmaker[AsyncSession] = session_factory) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None
        self.posts: PostRepository
        self.workspaces: WorkspaceRepository
        self.brand_profiles: BrandProfileRepository
        self.platform_connections: PlatformConnectionRepository
        self.social_accounts: SocialAccountRepository
        self.campaigns: CampaignRepository
        self.content_items: ContentItemRepository
        self.media_assets: MediaAssetRepository
        self.publications: PublicationRepository
        self.publication_attempts: PublicationAttemptRepository
        self.ai_generations: AIGenerationRepository

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.posts = SqlAlchemyPostRepository(self._session)
        self.workspaces = SqlAlchemyWorkspaceRepository(self._session)
        self.brand_profiles = SqlAlchemyBrandProfileRepository(self._session)
        self.platform_connections = SqlAlchemyPlatformConnectionRepository(self._session)
        self.social_accounts = SqlAlchemySocialAccountRepository(self._session)
        self.campaigns = SqlAlchemyCampaignRepository(self._session)
        self.content_items = SqlAlchemyContentItemRepository(self._session)
        self.media_assets = SqlAlchemyMediaAssetRepository(self._session)
        self.publications = SqlAlchemyPublicationRepository(self._session)
        self.publication_attempts = SqlAlchemyPublicationAttemptRepository(self._session)
        self.ai_generations = SqlAlchemyAIGenerationRepository(self._session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered")
        await self._session.commit()


async def dispose_engine() -> AsyncIterator[None]:
    yield
    await engine.dispose()
