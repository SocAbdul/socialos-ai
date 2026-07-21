# Architecture decision record: initial platform foundation

## Context

SocialOS AI must support many tenants, social providers, and asynchronous
publishing workflows without coupling business rules to frameworks or vendors.

## Decision

The API follows four dependency layers:

1. **Domain** owns entities, value objects, errors, and provider-neutral rules.
2. **Application** owns use cases and ports for persistence and publishing.
3. **Infrastructure** implements PostgreSQL, Redis/Celery, and external providers.
4. **Presentation** maps HTTP contracts to application commands.

Dependencies point inward. FastAPI and SQLAlchemy types do not enter the domain.
Each request carries an authenticated actor and organization context. Repository
queries always require the organization identifier.

Publishing is an asynchronous state machine:

`draft -> scheduled -> publishing -> published | partially_failed | failed`

Database writes and task dispatch will use a transactional outbox before real
provider delivery is enabled. This prevents losing a publish request between a
database commit and Redis enqueue.

## Initial aggregate

`SocialPost` owns source content and one or more `PostTarget` records. Targets
contain the platform-neutral lifecycle plus provider-returned external IDs.
Provider credentials are deliberately not part of this aggregate and will be
stored encrypted in a separate `SocialConnection` aggregate.

