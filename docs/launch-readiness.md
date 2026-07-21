# Public launch readiness

The repository has a production-grade foundation, but it must not receive public
traffic until every launch gate below is complete and verified in staging.

## Implemented foundation

- Clean Architecture boundaries with domain, application, infrastructure and
  presentation layers.
- PostgreSQL persistence, Alembic migrations, Redis and Celery.
- Docker development and production images.
- Clerk session verification, Organizations tenancy and role-based permissions.
- Tenant-scoped post storage and provider-agnostic publishing ports.
- CI checks, dependency auditing and Terraform foundations for media delivery.

## Required launch gates

- **Authentication:** provision production Clerk, complete the verification in
  `authentication.md`, and store secrets in AWS.
- **Billing:** implement Stripe Checkout, subscriptions, webhooks, entitlements,
  idempotency and a customer portal.
- **Social providers:** implement and review each OAuth connector independently,
  including token encryption, refresh, revocation, rate limits and webhooks.
- **Infrastructure:** provision production VPC, RDS, ElastiCache, ECS, ALB,
  CloudFront, S3, DNS, TLS, WAF and least-privilege IAM through Terraform.
- **Reliability:** add structured error tracking, metrics, traces, dashboards,
  paging, dead-letter queues, retry policies and restore-tested backups.
- **Security:** complete threat modeling, dependency and container scanning,
  secret rotation, encryption review, rate limiting and an external penetration
  test.
- **Product operations:** add transactional email, support workflows, account
  deletion/export, audit logs and an incident response runbook.
- **Compliance:** publish Terms, Privacy and Cookie policies and complete GDPR
  consent, retention and data-processing procedures.
- **Quality:** exercise end-to-end tests against staging, load test critical
  paths, test migrations on a production-like snapshot and execute rollback and
  disaster-recovery drills.

## Release rule

Promote an immutable image digest from staging to production only after all CI,
staging smoke tests and the launch checklist pass. Run database migrations as a
one-off ECS task before shifting traffic, and use a reversible deployment for
application containers.
