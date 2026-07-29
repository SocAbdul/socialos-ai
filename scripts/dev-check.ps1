Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Write-Host "Checking Docker Compose configuration..."
Push-Location $root
docker compose config | Out-Null
Pop-Location

Write-Host "Checking backend..."
Push-Location (Join-Path $root "apps/api")
uv sync --all-groups --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
uv run python -c "from socialos.main import app; print(app.title)"
Pop-Location

Write-Host "Checking frontend..."
Push-Location (Join-Path $root "apps/web")
npm ci
npm audit --omit=dev --audit-level=high
npm run lint
npm run typecheck
npm test
npm run build
Pop-Location

Write-Host "All local checks passed."
