# AWS staging bootstrap runbook

This runbook prepares the first SocialOS AI staging environment without static
AWS access keys in GitHub Actions.

Do not run `terraform apply` until the AWS account, budget, domain and execution
role are approved.

## 1. Bootstrap Terraform remote state

Terraform state contains sensitive values, including generated staging database
credentials. Create the remote state bucket and lock table first, using a trusted
operator session:

```powershell
cd C:\dev\socialos-ai\infra\bootstrap\state
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out bootstrap-state.tfplan
terraform apply bootstrap-state.tfplan
```

Use globally unique `state_bucket_name`.

After apply, record:

- `state_bucket_name`
- `lock_table_name`

## 2. Configure GitHub staging environment variables

Configure these variables in the GitHub `staging` environment:

- `AWS_REGION`
- `AWS_TERRAFORM_PLAN_ROLE_ARN`
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

Optional variables:

- `ENABLE_STAGING_RUNTIME`
- `EXISTING_GITHUB_OIDC_PROVIDER_ARN`
- `STAGING_DESIRED_COUNT`
- `STAGING_API_IMAGE`
- `STAGING_WEB_IMAGE`
- `CLERK_AUDIENCE`
- `META_APP_ID`
- `META_APP_SECRET_ARN`
- `STAGING_SECRET_KMS_KEY_ARNS_HCL`

`STAGING_SECRET_KMS_KEY_ARNS_HCL` must be an HCL list, for example:

```hcl
["arn:aws:kms:eu-west-1:123456789012:key/00000000-0000-0000-0000-000000000000"]
```

Use `[]` or leave empty when using AWS-managed service keys.

## 3. Publish staging images

For the first foundation apply, keep `ENABLE_STAGING_RUNTIME=false` or unset.
This creates the ECR repositories before ECS tries to run images.

Run the manual GitHub Actions workflow:

```text
Publish Staging Images
```

Use `main` as `git_ref` after CI is green. Copy the emitted immutable API and web
image refs into:

- `STAGING_API_IMAGE`
- `STAGING_WEB_IMAGE`

Then set `ENABLE_STAGING_RUNTIME=true` for the second staging plan.

The web image is built with `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. If that key
changes, publish a new web image tag.

## 4. Run Terraform plan

Run the manual GitHub Actions workflow:

```text
Terraform Plan
```

Review the plan before any apply. The workflow initializes the staging backend
with:

- `TF_STATE_BUCKET`
- `TF_LOCK_TABLE`
- key `socialos-ai/staging/terraform.tfstate`

## 5. Apply only with explicit approval

Do not apply automatically. A human should verify:

- budget alerts;
- expected monthly cost;
- domain and Clerk settings;
- S3 bucket name;
- immutable image refs;
- secret ARNs;
- Terraform state backend encryption and access controls.

After apply, run migrations as a controlled one-off ECS task before routing real
traffic.
