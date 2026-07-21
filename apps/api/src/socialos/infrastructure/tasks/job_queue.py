from datetime import UTC, datetime
from uuid import UUID

from socialos.infrastructure.tasks.publications import publish_publication_task


class CeleryJobQueue:
    async def enqueue_publication(
        self, publication_id: UUID, run_at: datetime | None = None
    ) -> None:
        eta = run_at.astimezone(UTC) if run_at else None
        publish_publication_task.apply_async(args=[str(publication_id)], eta=eta)
