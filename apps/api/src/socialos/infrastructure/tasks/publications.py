import asyncio
from uuid import UUID

from socialos.application.social.use_cases import PublishQueuedPublication
from socialos.config import get_settings
from socialos.infrastructure.database.session import SqlAlchemyUnitOfWork, engine
from socialos.infrastructure.security.token_cipher import FernetTokenCipher
from socialos.infrastructure.social.local_dev import LocalDevelopmentSocialProvider
from socialos.infrastructure.social.meta import MetaSocialProvider
from socialos.infrastructure.tasks.celery_app import celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="socialos.publish_publication", autoretry_for=(), max_retries=0
)
def publish_publication_task(publication_id: str) -> None:
    asyncio.run(_publish_and_dispose(UUID(publication_id)))


async def _publish_and_dispose(publication_id: UUID) -> None:
    try:
        await _publish(publication_id)
    finally:
        await engine.dispose()


async def _publish(publication_id: UUID) -> None:
    settings = get_settings()
    cipher = FernetTokenCipher(settings.token_encryption_key)
    meta = MetaSocialProvider(settings, cipher)
    local_dev = LocalDevelopmentSocialProvider()
    use_case = PublishQueuedPublication(
        SqlAlchemyUnitOfWork,
        providers={meta.provider_name: meta, local_dev.provider_name: local_dev},
    )
    await use_case.execute(publication_id)
