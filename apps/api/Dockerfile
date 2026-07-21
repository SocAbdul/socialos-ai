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

FROM base AS production
RUN uv sync --no-dev --frozen --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --no-dev --frozen
USER appuser
CMD ["uvicorn", "socialos.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
