# SocialOS AI

AI-powered multi-platform marketing operating system.

## Architecture

This monorepo contains:

- `apps/api`: FastAPI, Python, SQLAlchemy, Alembic, Celery.
- `apps/web`: Next.js, React, TypeScript, TailwindCSS.
- `infra`: Terraform foundations.
- `docs`: launch, platform-access and runbook documentation.

The product uses clean architecture and provider-based social connectors. Meta is
`VERIFIED_IN_DEVELOPMENT`: real Kinetic Mobiles Facebook and Instagram image posts were
published successfully through the official API. Meta App Review and Live mode remain
required before customer-facing production use.

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
uv run ruff format --check .
uv run mypy src tests
uv run pytest
uv run python -c "from socialos.main import app; print(app.title)"
uv run alembic upgrade head
```

Frontend:

```powershell
cd C:\dev\socialos-ai\apps\web
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm test
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

`MEDIA_STORAGE_PROVIDER=local-public` stores validated JPEG/PNG uploads in a persistent local mount for the zero-cost preview. The dashboard uploads files directly to the API and stores only metadata in PostgreSQL. Staging and production still require `MEDIA_STORAGE_PROVIDER=s3`. See `docs/runbooks/media-storage.md`.

Never paste `META_APP_SECRET`, authorization codes, access tokens, AWS secrets or signed media URLs into chat or logs.

## Staging deployment preparation

The reviewed staging target is a single Hetzner VM with Cloudflare R2 media storage. The repository currently prepares deployment only; it does not provision or contact either provider.

```powershell
Copy-Item .env.staging.example .env.staging
# Populate the ignored file through a secure channel, then validate offline:
python scripts/staging_preflight.py --env-file .env.staging
docker compose --env-file .env.staging -f docker-compose.staging.yml config --quiet
```

See [Hetzner staging deployment](docs/runbooks/hetzner-staging-deployment.md), [R2 configuration](docs/runbooks/r2-staging-configuration.md), [PostgreSQL backup/restore](docs/runbooks/postgres-backup-restore.md), [Meta cutover](docs/runbooks/meta-staging-cutover.md), and the [security checklist](docs/operations/staging-security-checklist.md).

> **COST BOUNDARY — 0 €:** no hosting, domain, bucket, DNS, billing, Meta change, OAuth, social publication or external deployment has been created or executed. Stop before the first provider account/resource action and obtain explicit authorization.
