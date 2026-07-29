from typing import Any

from fastapi.testclient import TestClient

from socialos.main import app
from socialos.presentation.api.health import DependencyCheck


def test_liveness_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ready_when_dependencies_are_healthy(monkeypatch: Any) -> None:
    async def healthy_database() -> DependencyCheck:
        return DependencyCheck(status="ok", latency_ms=1)

    async def healthy_redis() -> DependencyCheck:
        return DependencyCheck(status="ok", latency_ms=2)

    monkeypatch.setattr("socialos.main.check_database", healthy_database)
    monkeypatch.setattr("socialos.main.check_redis", healthy_redis)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ready",
        "environment": payload["environment"],
        "version": "0.1.0",
        "dependencies": {
            "database": {"status": "ok", "latency_ms": 1, "error": None},
            "redis": {"status": "ok", "latency_ms": 2, "error": None},
        },
    }
    assert payload["environment"] in {"local", "test"}


def test_readiness_returns_503_when_a_dependency_fails(monkeypatch: Any) -> None:
    async def healthy_database() -> DependencyCheck:
        return DependencyCheck(status="ok", latency_ms=1)

    async def failing_redis() -> DependencyCheck:
        return DependencyCheck(status="error", latency_ms=2, error="ConnectionError")

    monkeypatch.setattr("socialos.main.check_database", healthy_database)
    monkeypatch.setattr("socialos.main.check_redis", failing_redis)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["dependencies"]["redis"] == {
        "status": "error",
        "latency_ms": 2,
        "error": "ConnectionError",
    }
