# Hetzner staging deployment runbook

Status: preparation only. No server, account, DNS record, bucket or paid resource is created by this repository.

## Target shape

- One existing Ubuntu 24.04 LTS Hetzner VM, minimum 2 vCPU, 4 GB RAM and 80 GB disk.
- Docker Engine with Compose v2; application checkout at `/opt/socialos`.
- Caddy is the only public container. TCP 80/443 and UDP 443 are public; SSH is restricted to operator IPs.
- API, worker, PostgreSQL and Redis use an internal Docker network and publish no host ports.
- Cloudflare R2 stores public publication media through the S3-compatible adapter.
- Images are referenced by an immutable 40-character `RELEASE_SHA`; `latest` is forbidden.

## Host preparation checklist (manual, after authorization)

1. Create a non-root deployment user with SSH keys; disable password and root SSH login.
2. Enable automatic security updates and a firewall allowing only restricted SSH plus 80/443.
3. Install Docker from its official repository and grant Docker access only to the deployment user.
4. Create `/opt/socialos` and `/var/backups/socialos` with restrictive ownership and permissions.
5. Configure Docker log rotation and monitor `/var/lib/docker`, the database volume and free inodes.
6. Copy `.env.staging.example` to ignored `.env.staging`, populate it through a secure channel and run `scripts/staging.sh prepare`.

These are instructions, not provisioning automation. Record the OS image, VM ID, firewall rules and operator fingerprints in the private operations system.

## Release sequence

```bash
export STAGING_ENV_FILE=/opt/socialos/.env.staging
./scripts/staging.sh prepare
./scripts/postgres-backup.sh
MIGRATION_CONFIRMATION=run-staging-migration ./scripts/staging.sh migrate
DEPLOY_CONFIRMATION=deploy-existing-staging-host ./scripts/staging.sh deploy
./scripts/staging.sh health
```

The deployment order is dependencies, one-shot Alembic migration, API/worker/web, then Caddy. Never run concurrent migrations. A release is accepted only when `/health/ready` reports the expected `RELEASE_SHA` and healthy dependencies.

## Rollback

Set `ROLLBACK_RELEASE_SHA` to a previously verified commit and run `scripts/staging.sh rollback`. This rolls application images back but never downgrades the database. Every migration must therefore be backward-compatible with the previous release or include an explicit forward-fix plan.

## Operations

- `scripts/staging.sh status` shows container and disk usage.
- Docker JSON logs rotate at 10 MB with five files per container. Ship logs off-host before claiming durable audit retention.
- Alert manually at 70% disk and act before 85%; check Docker layers, database growth, backups and logs.
- Do not put secrets in shell history, Compose files, GitHub variables intended for non-secrets, or logs.
- Production requires a separate architecture and approval; this single-node design is staging only.

## Future CI/CD boundary

A future workflow may connect to an already approved host, pull SHA-tagged images and invoke these scripts. It must use environment approval, pinned actions, least-privilege registry/SSH credentials and must not provision infrastructure. This PR intentionally does not add credentials, provider calls or deployment execution.
