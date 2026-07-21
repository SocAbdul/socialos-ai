# SocialOS AI

AI-powered multi-platform marketing operating system.

## Architecture

This monorepo contains:

- `apps/api`: FastAPI, Python, SQLAlchemy, Alembic, Celery.
- `apps/web`: Next.js, React, TypeScript, TailwindCSS.
- `infra`: Terraform foundations.
- `docs`: launch, platform-access and runbook documentation.

The product uses clean architecture and provider-based social connectors. Meta is currently `IMPLEMENTED_NOT_VERIFIED` until one real Kinetic Mobiles Facebook post and one real Instagram post are published from SocialOS AI.

## Quick Start Para Windows

Use a path outside OneDrive:

```powershell
cd C:\dev
git clone <repo-url> socialos-ai
cd C:\dev\socialos-ai
Copy-Item .env.example .env
```

Install backend dependencies:

```powershell
cd C:\dev\socialos-ai\apps\api
uv sync --all-groups
```

Install frontend dependencies:

```powershell
cd C:\dev\socialos-ai\apps\web
npm ci
```

Validate Docker Compose:

```powershell
cd C:\dev\socialos-ai
docker compose config
```

Start PostgreSQL and Redis:

```powershell
docker compose up -d postgres redis
docker compose ps
```

Run database migrations:

```powershell
cd C:\dev\socialos-ai\apps\api
uv run alembic upgrade head
```

Start FastAPI:

```powershell
cd C:\dev\socialos-ai\apps\api
uv run uvicorn socialos.main:app --reload --host 0.0.0.0 --port 8000
```

Start the Celery worker in a second terminal:

```powershell
cd C:\dev\socialos-ai\apps\api
uv run celery -A socialos.infrastructure.tasks.celery_app worker --loglevel=INFO
```

Start the frontend in a third terminal:

```powershell
cd C:\dev\socialos-ai\apps\web
npm run dev
```

Open:

- Frontend: `http://localhost:3000`
- API health: `http://localhost:8000/health/live`
- API docs: `http://localhost:8000/docs`

## Demo Mode

To review the UI without Meta or the backend:

```powershell
cd C:\dev\socialos-ai
$env:NEXT_PUBLIC_DEMO_MODE="true"
cd apps\web
npm run dev
```

Then open `http://localhost:3000`.

## Validation Commands

Backend:

```powershell
cd C:\dev\socialos-ai\apps\api
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run python -c "from socialos.main import app; print(app.title)"
uv run alembic upgrade head
```

Frontend:

```powershell
cd C:\dev\socialos-ai\apps\web
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm run dev
```

Infrastructure:

```powershell
cd C:\dev\socialos-ai
docker compose config
docker compose up --build
docker compose ps
```

All-in-one local checks:

```powershell
cd C:\dev\socialos-ai
.\scripts\dev-check.ps1
```

Start local stack:

```powershell
cd C:\dev\socialos-ai
.\scripts\start-local.ps1
```

## Environment Notes

`AUTH_MODE=development` accepts local development headers only in local/test environments. `AUTH_MODE=clerk` verifies Clerk JWTs.

Never paste `META_APP_SECRET`, authorization codes, access tokens or signed media URLs into chat or logs.
