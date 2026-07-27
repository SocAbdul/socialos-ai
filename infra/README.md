# Infrastructure

Terraform is separated into reusable modules and environment compositions.
Remote state, AWS account IDs, DNS zones, and secrets are environment-owned and
must never be committed.

The initial module creates the secure artifact layer used by every environment:

- private, versioned S3 media bucket;
- public access fully blocked;
- KMS-backed server-side encryption;
- lifecycle rules for incomplete multipart uploads;
- CloudFront origin access control and distribution;
- least-privilege IAM policy for the API identity that signs direct uploads.

ECS, RDS, ElastiCache, networking, WAF, observability, and deployment roles will
be added as independent modules after the AWS account and environment topology
are confirmed.

The staging composition also prepares:

- monthly AWS Budget alerts;
- immutable ECR repositories for API and web images;
- GitHub Actions OIDC deployment role for pushing verified images without
  long-lived AWS access keys.
- low-cost ECS Fargate runtime behind an Application Load Balancer for staging
  smoke tests.
- private RDS PostgreSQL and ElastiCache Redis foundations for staging state.

If the AWS account already has a GitHub Actions OIDC provider, set
`existing_github_oidc_provider_arn` in the staging tfvars instead of creating a
duplicate provider.

The staging runtime intentionally uses public subnets with tightly scoped
security groups to avoid NAT Gateway cost during private beta. This is acceptable
only for staging validation. Production must use private service subnets, TLS,
WAF, managed databases and a reviewed network topology before public traffic.

## Staging media foundation

Create a local tfvars file from the example:

```powershell
cd C:\dev\socialos-ai\infra\environments\staging
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with a globally unique bucket name and the real staging
frontend origin. Then validate:

```powershell
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out staging-media.tfplan
```

Do not run `terraform apply` until the AWS account, state backend, IAM execution
identity, budget alarms and staging domain are confirmed.

After apply, configure the API environment from outputs:

```env
MEDIA_STORAGE_PROVIDER=s3
S3_MEDIA_BUCKET=<media_bucket_name>
S3_MEDIA_REGION=<aws_region>
S3_MEDIA_PUBLIC_BASE_URL=<media_public_base_url>
```

Attach `media_signer_policy_arn` to the API runtime identity. Prefer an ECS task
role or GitHub OIDC-assumed role over static access keys.

## GitHub Actions Terraform plan

`.github/workflows/terraform-plan.yml` is manual-only. It does not apply
infrastructure. Before it can run, configure the GitHub `staging` environment
variables:

- `AWS_TERRAFORM_PLAN_ROLE_ARN`
- `AWS_REGION`
- `TF_STATE_BUCKET`
- `TF_LOCK_TABLE`
- `S3_MEDIA_BUCKET`
- `STAGING_WEB_ORIGIN`
- `MONTHLY_BUDGET_LIMIT_USD`
- `BUDGET_ALERT_EMAIL`
- `STAGING_API_IMAGE`
- `STAGING_WEB_IMAGE`
- `CLERK_JWKS_URL`
- `CLERK_ISSUER`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `TOKEN_ENCRYPTION_KEY_SECRET_ARN`
- `CLERK_SECRET_KEY_SECRET_ARN`

Set `ENABLE_STAGING_RUNTIME=false` or leave it unset for the first foundation
apply. After ECR exists and images are published, set `ENABLE_STAGING_RUNTIME=true`
and provide `STAGING_API_IMAGE` plus `STAGING_WEB_IMAGE`.

The first Terraform bootstrap may still need to be run by an AWS administrator
because the OIDC roles do not exist before Terraform is applied.

Remote state bootstrap lives in `infra/bootstrap/state`. Follow
`docs/runbooks/aws-staging-bootstrap.md` before running a real staging plan.

## GitHub Actions staging image publication

`.github/workflows/publish-staging-images.yml` is manual-only. It publishes
immutable Docker images to the staging ECR repositories after verifying that the
selected commit SHA has a successful completed CI run.

Configure these GitHub `staging` environment variables before running it:

- `AWS_REGION`
- `AWS_STAGING_DEPLOY_ROLE_ARN`
- `STAGING_API_ECR_REPOSITORY_URL`
- `STAGING_WEB_ECR_REPOSITORY_URL`
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

Use these Terraform outputs after staging bootstrap:

- `github_actions_deploy_role_arn` -> `AWS_STAGING_DEPLOY_ROLE_ARN`
- `ecr_repository_urls["api"]` -> `STAGING_API_ECR_REPOSITORY_URL`
- `ecr_repository_urls["web"]` -> `STAGING_WEB_ECR_REPOSITORY_URL`

Images are tagged with the full commit SHA. Do not use mutable tags such as
`latest` for staging or production promotion.

The web image is built with `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. If the Clerk
publishable key changes, publish a new immutable web image tag.

## Staging runtime

The staging environment now composes:

- VPC with two public subnets and two private isolated subnets;
- internet-facing Application Load Balancer;
- ECS Fargate cluster;
- API and web services;
- private RDS PostgreSQL instance;
- private ElastiCache Redis replication group;
- CloudWatch log groups;
- ECS task execution and task roles;
- media signing IAM policy attached to the API/web task role;
- runtime secrets injected by ARN from SSM Parameter Store or Secrets Manager.

Before applying the staging runtime, publish immutable images with
`publish-staging-images.yml` and set:

- `staging_api_image`
- `staging_web_image`
- `staging_api_secret_arns`
- `staging_web_secret_arns`

The staging PostgreSQL module generates `DATABASE_URL` in Secrets Manager and
passes its secret ARN to ECS. This keeps the value out of GitHub logs and task
definitions, but the generated password is still present in Terraform state.
Use encrypted remote state with strict IAM before applying. For production,
review secret provisioning and rotation before reuse.

`REDIS_URL` is configured as a non-secret environment variable because the
staging Redis cluster is private and VPC-restricted. Production Redis must
revisit auth, TLS, service-specific security groups and subnet design.

Do not store secret values in Terraform variables or GitHub workflow logs.

## GitHub Actions staging operations

After the staging runtime exists, use `docs/runbooks/staging-operations.md` for:

- running Alembic migrations as a one-off ECS task;
- waiting for API and web ECS services to become stable;
- checking API health and the web entrypoint through the load balancer.

These workflows are manual-only and scoped to the GitHub `staging` environment.
