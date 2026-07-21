from celery import Celery

from socialos.config import get_settings

settings = get_settings()
celery_app = Celery("socialos", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
celery_app.autodiscover_tasks(["socialos.infrastructure.tasks"])
