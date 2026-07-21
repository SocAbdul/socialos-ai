from datetime import datetime
from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    async def enqueue_publication(
        self, publication_id: UUID, run_at: datetime | None = None
    ) -> None: ...
