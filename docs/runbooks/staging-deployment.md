# Staging deployment runbook

This is an architecture contract, not evidence that staging exists.

1. Allocate a stable domain and HTTPS certificates for app, API and public media.
2. Create private PostgreSQL and Redis endpoints; do not expose either publicly.
3. Create an S3-compatible private upload bucket with an approved public delivery origin.
4. Store database, authentication, encryption, Meta and object-storage secrets in a secret manager.
5. Build immutable API and web images tagged with the tested Git SHA.
6. Populate the environment schema represented by `.env.staging.example` without committing values.
7. Run exactly one release migration job: `alembic upgrade head`.
8. Start API, worker and web from immutable images without source bind mounts.
9. Route `/` to web, `/api/*` and `/health/*` to API, and `/media/*` to the public-media origin when applicable.
10. Verify `/health/live`, `/health/ready`, worker broker ping and the web health check.
11. Only after Meta configuration is separately approved, register the stable callback URI and run supervised OAuth smoke tests.
12. Smoke-test workspace isolation, upload, local/test publication paths and failure recovery.
13. On failure, stop rollout, preserve logs and database state, and redeploy the previous immutable image. Apply a database rollback only when a tested downgrade is explicitly safe.

Never run migrations concurrently from every API replica. Never use `latest` as the release identity.
