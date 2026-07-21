.PHONY: install dev test lint format compose-up compose-down migrate

install:
	cd apps/api && uv sync --all-groups
	cd apps/web && npm install

dev:
	docker compose up --build

test:
	cd apps/api && uv run pytest
	cd apps/web && npm test

lint:
	cd apps/api && uv run ruff check .
	cd apps/api && uv run mypy src
	cd apps/web && npm run lint
	cd apps/web && npm run typecheck

format:
	cd apps/api && uv run ruff format .
	cd apps/web && npm run format

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

migrate:
	cd apps/api && uv run alembic upgrade head

