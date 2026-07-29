# Contributing To SocialOS AI

## Development Principles

- Keep the domain model platform-neutral.
- Put provider-specific logic behind provider interfaces.
- Do not expose tokens, authorization codes, app secrets, or signed media URLs.
- Prefer small pull requests with clear acceptance criteria.
- Add tests proportional to the risk of the change.

## Local Setup

Use `C:\dev\socialos-ai` on Windows to avoid OneDrive locking `node_modules`.

```powershell
Copy-Item .env.example .env
cd apps\api
uv sync --all-groups --frozen
cd ..\web
npm ci
```

## Required Checks

Backend:

```powershell
cd apps\api
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
uv run python -c "from socialos.main import app; print(app.title)"
```

Frontend:

```powershell
cd apps\web
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Repository:

```powershell
docker compose config
```

## Pull Request Flow

1. Create a branch from `main`.
2. Make a focused change.
3. Run relevant checks locally.
4. Open a draft PR early.
5. Move to ready only after CI passes and the PR has clear validation notes.
6. Merge through GitHub, not by pushing directly to `main`.
