from socialos.infrastructure.tasks.celery_app import celery_app


def test_celery_imports_publication_tasks() -> None:
    assert "socialos.infrastructure.tasks.publications" in celery_app.conf.imports
