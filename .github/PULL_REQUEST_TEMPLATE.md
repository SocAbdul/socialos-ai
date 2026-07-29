## Summary

- 

## Why

- 

## Validation

- [ ] `cd apps/api && uv run ruff check .`
- [ ] `cd apps/api && uv run ruff format --check .`
- [ ] `cd apps/api && uv run mypy src tests`
- [ ] `cd apps/api && uv run pytest`
- [ ] `cd apps/api && uv run python -c "from socialos.main import app; print(app.title)"`
- [ ] `cd apps/web && npm audit --omit=dev --audit-level=high`
- [ ] `cd apps/web && npm run lint`
- [ ] `cd apps/web && npm run typecheck`
- [ ] `cd apps/web && npm test`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/web && npm run test:e2e`
- [ ] `docker compose config`

## Deployment Notes

- [ ] No new secrets required
- [ ] Database migration reviewed
- [ ] Rollback path documented
