from uuid import uuid4

import pytest
import structlog

from socialos.infrastructure.tasks.job_queue import CeleryJobQueue
from socialos.infrastructure.tasks.publications import publish_publication_task


@pytest.mark.asyncio
async def test_job_queue_propagates_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def apply_async(*, args: list[object], eta: object) -> None:
        captured.update(args=args, eta=eta)

    monkeypatch.setattr(publish_publication_task, "apply_async", apply_async)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="request-correlation-123")
    publication_id = uuid4()

    await CeleryJobQueue().enqueue_publication(publication_id)
    structlog.contextvars.clear_contextvars()

    assert captured == {
        "args": [str(publication_id), "request-correlation-123"],
        "eta": None,
    }
