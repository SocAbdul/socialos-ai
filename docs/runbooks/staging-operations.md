# Staging operations runbook

This runbook covers the manual staging operations that happen after the staging Terraform foundation and runtime are applied.

These operations are intentionally manual while SocialOS AI is pre-launch. They must run only from the GitHub `staging` environment and must not be copied to production without a separate production approval workflow.

## Required GitHub staging variables

Set these as GitHub environment variables on the `staging` environment:

| Variable | Source |
| --- | --- |
| `AWS_REGION` | Existing staging region, for example `eu-west-1`. |
| `AWS_STAGING_DEPLOY_ROLE_ARN` | Terraform output `github_actions_deploy_role_arn`. |
| `STAGING_ECS_CLUSTER_NAME` | Terraform output `staging_ecs_cluster_name`. |
| `STAGING_API_SERVICE_NAME` | Terraform output `staging_api_service_name`. |
| `STAGING_WEB_SERVICE_NAME` | Terraform output `staging_web_service_name`. |
| `STAGING_ALB_URL` | Terraform output `staging_alb_dns_name`, optionally prefixed with `http://`. |
| `STAGING_API_TASK_DEFINITION_ARN` | Terraform output `staging_api_task_definition_arn`. |
| `STAGING_PUBLIC_SUBNET_IDS_JSON` | Terraform output `public_subnet_ids` encoded as JSON, for example `["subnet-abc","subnet-def"]`. |
| `STAGING_SERVICE_SECURITY_GROUP_ID` | Terraform output `staging_service_security_group_id`. |

## Run smoke checks

Use this after a staging deployment or after changing runtime configuration.

1. Open GitHub Actions.
2. Select **Staging Smoke**.
3. Click **Run workflow** on `main`.
4. Wait for:
   - ECS API service stable.
   - ECS web service stable.
   - API health check passing through the load balancer.
   - Web entrypoint responding through the load balancer.

The smoke workflow does not mutate application data.

## Run database migrations

Use this after deploying an API image that includes new Alembic revisions.

1. Confirm the staging database backup posture is acceptable for the current phase.
2. Confirm the API image deployed to staging contains the intended migration revisions.
3. Open GitHub Actions.
4. Select **Staging Migrations**.
5. Click **Run workflow** on `main`.
6. Enter the exact confirmation:

   ```text
   run-staging-migrations
   ```

The workflow starts a one-off ECS Fargate task from the API task definition and overrides the command to:

```bash
alembic upgrade head
```

The workflow waits for the task to stop and fails if the API container exits with a non-zero code.

## Recommended order for staging deploy validation

1. Publish staging images.
2. Apply Terraform/runtime changes manually from a controlled operator workstation.
3. Run **Staging Migrations** if the API image includes database migrations.
4. Run **Staging Smoke**.
5. Manually verify the product flow from the browser.
6. Promote only after the staging result is understood.

## Guardrails

- Do not run these workflows against production.
- Do not bypass the `staging` environment approval rules.
- Do not run migrations while another migration task is active.
- Do not change GitHub environment variables from inside CI.
- Do not store secrets as variables; use AWS Secrets Manager/SSM and Terraform secret ARN references.
