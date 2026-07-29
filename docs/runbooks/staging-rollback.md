# Staging rollback runbook

This runbook describes how to recover staging after a bad application deployment,
failed migration, or degraded smoke test.

It is intentionally written for staging only. Production rollback must have a
separate approval process, tested backups and a reviewed data-migration policy.

## When to use this runbook

Use this runbook when one or more of these are true:

- `Staging Smoke` fails after a deployment.
- The API or web ECS service cannot become stable.
- The API health endpoint returns unhealthy dependency status.
- A newly deployed image causes regressions in the main browser flow.
- A one-off migration task exits non-zero.

## Information to capture first

Before changing anything, capture enough context for the postmortem:

```powershell
gh run list --workflow CI --limit 5
gh run list --workflow "Publish Staging Images" --limit 5
gh run list --workflow "Staging Smoke" --limit 5
```

From AWS/ECS, capture:

- current API task definition ARN;
- current web task definition ARN;
- current API image URI;
- current web image URI;
- failed task stopped reason;
- latest API/web CloudWatch log excerpts;
- whether a migration task ran and its exit code.

Do not paste secrets, database URLs or token values into GitHub issues.

## Fast rollback for application images

Use this when the infrastructure is healthy and only the new application image is
suspect.

1. Identify the last known-good commit SHA from the previous successful staging
   validation.
2. Confirm immutable images exist in ECR for that SHA:

   ```powershell
   aws ecr describe-images --repository-name socialos-staging-api --image-ids imageTag=<good-commit-sha>
   aws ecr describe-images --repository-name socialos-staging-web --image-ids imageTag=<good-commit-sha>
   ```

3. Update staging Terraform variables locally or in the controlled operator
   workspace:

   ```hcl
   staging_api_image = "<api-ecr-repository-url>:<good-commit-sha>"
   staging_web_image = "<web-ecr-repository-url>:<good-commit-sha>"
   ```

4. Run a Terraform plan and confirm that only ECS task definitions/services will
   change.
5. Apply from the approved operator workstation.
6. Run `Staging Smoke`.
7. Manually verify the dashboard and main publish flow.

## Rollback after a migration

Database rollbacks are riskier than container rollbacks.

Use this decision tree:

- If the migration failed before changing data, fix the migration and rerun in
  staging.
- If the migration changed schema only and Alembic has a safe downgrade, review
  the downgrade SQL before running it.
- If the migration changed data, prefer forward-fix migrations unless a tested
  snapshot restore is faster and safer.
- If data correctness is unknown, stop promotion and open an incident issue.

Never run an unreviewed destructive downgrade against shared staging data.

## Run a downgrade only after review

If a downgrade is explicitly approved for staging, run it as a one-off ECS task
using the same mechanics as `Staging Migrations`, but override the command with a
reviewed Alembic target:

```bash
alembic downgrade <revision>
```

Record the exact revision, operator, timestamp and reason in the incident issue.

## Smoke verification after rollback

Rollback is not complete until all of these pass:

- ECS API and web services are stable.
- API liveness endpoint returns 200.
- API readiness endpoint returns 200 and dependencies are healthy.
- Web entrypoint returns 200.
- Dashboard loads in a browser.
- A basic non-production publish workflow can be exercised safely.

## Post-rollback follow-up

Create or update a GitHub issue with:

- bad commit SHA;
- rollback commit/image SHA;
- failed checks and logs;
- customer/user impact, if any;
- root cause hypothesis;
- permanent fix owner;
- whether a migration or data correction is still pending.

Do not retry production promotion until the permanent fix has passed CI, staging
migrations and staging smoke checks.
