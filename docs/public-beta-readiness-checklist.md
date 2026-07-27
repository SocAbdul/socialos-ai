# Public beta readiness checklist

SocialOS AI must not accept public traffic until every critical gate below is
complete, verified and linked from the launch issue.

This checklist is intentionally stricter than a demo checklist. A public beta can
still be small, but it must be safe, recoverable and honest about what is real.

## 1. Product scope

- [ ] The public beta scope is written in the launch issue.
- [ ] Stripe/billing is explicitly disabled or hidden until approved.
- [ ] Only Meta is exposed as a real social provider.
- [ ] Any non-Meta provider UI is marked as planned, disabled or removed.
- [ ] Demo mode is disabled in staging/public runtime.
- [ ] Users can understand the next action without reading documentation.

## 2. Authentication and tenancy

- [ ] Clerk production instance exists.
- [ ] Clerk Organizations are enabled.
- [ ] Redirect URLs match the public domain and staging domain.
- [ ] `AUTH_MODE=clerk` outside local/test.
- [ ] `CLERK_JWKS_URL` and `CLERK_ISSUER` are configured.
- [ ] Authorized parties are restricted to real frontend origins.
- [ ] Users cannot access another workspace by changing IDs in the URL/API.
- [ ] Onboarding handles missing organization/workspace cleanly.

## 3. Meta integration

- [ ] Meta App is configured for the real callback URL.
- [ ] Required OAuth permissions are documented in `docs/platform-access/meta.md`.
- [ ] Kinetic Mobiles has a compatible Facebook Page.
- [ ] Kinetic Mobiles has a compatible Instagram professional account.
- [ ] A real Facebook image/text post has been published through SocialOS AI.
- [ ] A real Instagram image/text post has been published through SocialOS AI.
- [ ] External publication URLs are stored and visible in the dashboard.
- [ ] Retryable failures do not create duplicate posts.
- [ ] Permanent failures show user-safe error messages.
- [ ] Token refresh/revocation behavior is documented.

## 4. Media storage

- [ ] Browser direct upload to S3 works in staging.
- [ ] Uploaded media is retrievable through CloudFront.
- [ ] Meta can fetch the CloudFront media URL.
- [ ] Upload size/type limits are enforced.
- [ ] Failed uploads do not create orphaned publication records.
- [ ] Bucket public access remains blocked.
- [ ] Signed upload TTL is short and documented.

## 5. AI content generation

- [ ] The beta uses a single AI Content Service.
- [ ] AI generation stores provider, model, prompt version and token usage.
- [ ] Input-hash cache avoids paying twice for identical generations.
- [ ] AI output can be edited before publication.
- [ ] AI failures do not block manually written publishing.
- [ ] Generated captions do not exceed declared provider capabilities.

## 6. Reliability and operations

- [ ] CI is green on the launch commit.
- [ ] Immutable API/web images exist for the launch commit.
- [ ] Terraform plan is reviewed before apply.
- [ ] Alembic migrations run as a one-off ECS task.
- [ ] Staging smoke passes after migrations.
- [ ] API liveness returns 200.
- [ ] API readiness returns 200 with database and Redis healthy.
- [ ] Web entrypoint returns 200.
- [ ] Rollback runbook has been rehearsed in staging.
- [ ] The previous known-good image SHA is recorded.
- [ ] CloudWatch logs are accessible to the operator.

## 7. Security

- [ ] `TOKEN_ENCRYPTION_KEY` is strong and not an example value.
- [ ] Social access tokens are encrypted at rest.
- [ ] Secrets are stored in AWS Secrets Manager/SSM, not GitHub logs.
- [ ] S3 is required outside local/test.
- [ ] Development auth is forbidden outside local/test.
- [ ] CORS origins are restricted.
- [ ] Security contact mailbox exists and is monitored.
- [ ] `/.well-known/security.txt` is accurate.
- [ ] Dependency audit results are reviewed.
- [ ] No secrets appear in repository history or workflow output.

## 8. Legal and support

- [ ] Privacy Policy is published.
- [ ] Terms of Service are published.
- [ ] Cookie notice/consent is handled if needed.
- [ ] Account deletion process is documented.
- [ ] Data export process is documented.
- [ ] Support contact is published and monitored.
- [ ] Incident owner and escalation path are written down.

## 9. Beta launch decision

The launch approver must record:

- launch commit SHA;
- API image URI;
- web image URI;
- staging smoke run URL;
- migration run URL, if any;
- known risks accepted for beta;
- rollback image SHA;
- go/no-go decision.

If any critical gate is incomplete, do not launch public traffic.
