from datetime import UTC, datetime
from uuid import UUID

import structlog

from socialos.infrastructure.tasks.publications import publish_publication_task


class CeleryJobQueue:
    async def enqueue_publication(
        self, publication_id: UUID, run_at: datetime | None = None
    ) -> None:
        eta = run_at.astimezone(UTC) if run_at else None
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        publish_publication_task.apply_async(
            args=[str(publication_id), request_id if isinstance(request_id, str) else None],
            eta=eta,
        )
