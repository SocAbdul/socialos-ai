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

If the AWS account already has a GitHub Actions OIDC provider, set
`existing_github_oidc_provider_arn` in the staging tfvars instead of creating a
duplicate provider.

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
- `S3_MEDIA_BUCKET`
- `STAGING_WEB_ORIGIN`
- `MONTHLY_BUDGET_LIMIT_USD`
- `BUDGET_ALERT_EMAIL`

The first Terraform bootstrap may still need to be run by an AWS administrator
because the OIDC roles do not exist before Terraform is applied.
