# Runtime Security Baseline

This document records the minimum runtime controls for SocialOS AI.

## Environment modes

Supported values are `local`, `test`, `staging`, and `production`. Development-header authentication is allowed only in `local` and `test`. Staging and production must use Clerk authentication.

## Token encryption

`TOKEN_ENCRYPTION_KEY` protects stored provider credentials. Outside local and test environments it must:

- be present;
- contain at least 32 characters;
- not use a documented example or local-development value;
- be stored in a managed secret store rather than committed to Git.

Generate a suitable value with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Rotating this value requires a credential re-encryption plan. Replacing it without migration makes existing encrypted provider credentials unreadable.

## Local Docker networking

The repository Docker Compose file is for development only. PostgreSQL and Redis are bound to `127.0.0.1` so they are not exposed to the local network. Production deployments must use private networking and managed credentials; they must not publish database or broker ports to the internet.

## Meta OAuth callback

Meta redirects the browser to the frontend callback route. The frontend then forwards the short-lived code and state to the authenticated backend using a POST body. The backend must send the same configured frontend redirect URI during the code exchange.

The random state value is already stored as a hash, bound to its user, workspace, provider and redirect URI, and consumed once. Do not prepend a second workspace or organization prefix before sending it to Meta.

## Deployment revision integrity

CD must deploy the exact commit SHA that successfully completed CI. A workflow triggered by `workflow_run` must use `github.event.workflow_run.head_sha`, not an unrelated workflow SHA.

The current staging and production jobs are contracts only. They do not represent a real cloud deployment until image publishing, infrastructure update, migrations, health verification, and rollback are implemented.

The staging image publication workflow is manual and publishes only immutable
commit-SHA image tags after verifying that the exact revision has a successful
completed CI run. It must use GitHub OIDC and must not use static AWS access
keys.

The staging ECS runtime is optimized for private-beta cost control. It may run
Fargate services in public subnets behind an ALB with service security groups
allowing only ALB-originated inbound traffic. This is not the production network
model; production must use private service subnets, TLS, WAF, private databases,
restricted egress and reviewed network boundaries.

Staging RDS PostgreSQL and Redis must be created in private isolated subnets.
Only the ECS service security group should be allowed to connect. The staging
PostgreSQL module generates `DATABASE_URL` in Secrets Manager; this keeps the
runtime value out of GitHub logs, but the generated password remains sensitive
Terraform state. Remote state must be encrypted and access-controlled before
apply.

## Production readiness checks

Before the first production deployment, verify:

- Clerk issuer, JWKS URL, audience and authorized parties;
- encrypted Meta credentials can be read after restart;
- PostgreSQL and Redis are private;
- migrations are executed once with a controlled failure path;
- API, web and worker health checks pass;
- staging smoke tests run before production approval;
- logs never include access tokens, authorization codes, app secrets or signed media URLs.
