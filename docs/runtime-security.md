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

## Production readiness checks

Before the first production deployment, verify:

- Clerk issuer, JWKS URL, audience and authorized parties;
- encrypted Meta credentials can be read after restart;
- PostgreSQL and Redis are private;
- migrations are executed once with a controlled failure path;
- API, web and worker health checks pass;
- staging smoke tests run before production approval;
- logs never include access tokens, authorization codes, app secrets or signed media URLs.
