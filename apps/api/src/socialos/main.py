from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from socialos.application.common.auth import AuthorizationError
from socialos.application.social.use_cases import (
    ApplicationNotFoundError,
    ConnectionAuthorizationError,
)
from socialos.config import get_settings
from socialos.domain.posts.entities import DomainValidationError
from socialos.infrastructure.database.session import engine
from socialos.presentation.api.posts import router as posts_router
from socialos.presentation.api.social import router as social_router

settings = get_settings()
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level),
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-User-Id",
        "X-Organization-Id",
        "X-Organization-Role",
    ],
)


@app.exception_handler(DomainValidationError)
async def domain_validation_handler(_: Request, exc: DomainValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
async def authorization_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(ApplicationNotFoundError)
async def not_found_handler(_: Request, exc: ApplicationNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConnectionAuthorizationError)
async def connection_authorization_handler(
    _: Request, exc: ConnectionAuthorizationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(posts_router, prefix="/api/v1")
app.include_router(social_router, prefix="/api/v1")
