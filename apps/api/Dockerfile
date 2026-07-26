FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN pip install --no-cache-dir uv \
    && useradd --create-home --uid 10001 appuser
COPY pyproject.toml uv.lock* ./

FROM base AS development
RUN uv sync --all-groups --frozen --no-install-project
COPY . .
RUN uv sync --all-groups --frozen
EXPOSE 8000

FROM base AS production-builder
RUN uv sync --no-dev --frozen --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --no-dev --frozen

FROM python:3.13-slim AS production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY --from=production-builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --from=production-builder --chown=appuser:appuser /app/src ./src
COPY --from=production-builder --chown=appuser:appuser /app/alembic.ini ./
COPY --from=production-builder --chown=appuser:appuser /app/migrations ./migrations
USER appuser
CMD ["uvicorn", "socialos.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
