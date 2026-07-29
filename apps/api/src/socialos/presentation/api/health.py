import asyncio
from dataclasses import dataclass
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from socialos.config import Settings, get_settings
from socialos.infrastructure.database.session import engine

DependencyStatus = Literal["ok", "error"]


@dataclass(frozen=True)
class DependencyCheck:
    status: DependencyStatus
    latency_ms: int
    error: str | None = None


async def check_database(database_engine: AsyncEngine = engine) -> DependencyCheck:
    started_at = asyncio.get_running_loop().time()
    try:
        async with database_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        return _dependency_error(started_at, exc)
    return _dependency_ok(started_at)


async def check_redis(settings: Settings | None = None) -> DependencyCheck:
    runtime_settings = settings or get_settings()
    started_at = asyncio.get_running_loop().time()
    client = Redis.from_url(runtime_settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        await client.ping()
    except Exception as exc:
        return _dependency_error(started_at, exc)
    finally:
        await client.aclose()
    return _dependency_ok(started_at)


def _dependency_ok(started_at: float) -> DependencyCheck:
    return DependencyCheck(status="ok", latency_ms=_elapsed_ms(started_at))


def _dependency_error(started_at: float, exc: Exception) -> DependencyCheck:
    return DependencyCheck(
        status="error",
        latency_ms=_elapsed_ms(started_at),
        error=exc.__class__.__name__,
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((asyncio.get_running_loop().time() - started_at) * 1000))
