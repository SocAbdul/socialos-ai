# Authentication and organization setup

SocialOS AI uses Clerk sessions as its identity boundary and Clerk Organizations
as its tenant boundary. The API never trusts organization or role values sent by
the browser; it derives them from a verified session token.

## Clerk dashboard

1. Create separate Clerk applications for development and production.
2. Enable Organizations and require every user to belong to an organization.
3. Disable personal accounts for the production application.
4. Keep the default `org:admin` and `org:member` roles. Do not rename them
   without updating the application permission map and its tests.
5. Add the exact production application origin to Clerk's allowed origins.
6. Configure production DNS before creating the production keys.

## Environment

Copy `.env.example` to `.env` for local development. To enable Clerk, set:

```dotenv
AUTH_MODE=clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
CLERK_JWKS_URL=https://<clerk-frontend-api>/.well-known/jwks.json
CLERK_ISSUER=https://<clerk-frontend-api>
CLERK_AUTHORIZED_PARTIES=https://app.example.com
```

Set `CLERK_AUDIENCE` only if the session token template includes an audience.
For multiple authorized frontends, use a comma-separated list. Production
values belong in AWS Secrets Manager or SSM Parameter Store, never in Git.

Because Next.js embeds public variables into the browser bundle, pass
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` as a Docker build argument as well as a
runtime environment variable. The publishable key is intentionally public; the
Clerk secret key must only be injected at runtime.

## Authorization model

- `org:admin`: post read/write and organization management.
- `org:member`: post read/write.
- Missing organization, pending enrollment, unknown roles and invalid tokens
  are denied.

The development header identity is intentionally unavailable when
`AUTH_MODE=clerk`.

## Production verification

Before enabling traffic:

1. Sign up and create an organization through `/onboarding`.
2. Verify admin and member access using separate users.
3. Verify a user cannot access another organization's posts.
4. Verify expired tokens, altered tokens and unapproved origins return `401`.
5. Rotate a Clerk key in staging and confirm JWKS refresh works.
