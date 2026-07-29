# GitHub Workflow

## Branching

- `main` is protected and deployable.
- Feature work uses `feature/<short-name>` or `agent/<short-name>`.
- Pull requests are opened as drafts until validation is complete.

## CI

Every pull request runs:

- Backend dependency audit, lint, format check, typecheck, migrations and tests.
- Frontend dependency audit, lint, typecheck, unit tests, build and Playwright demo flow.
- Terraform format, staging tfvars generation and validation for infrastructure environments.
- Production Docker image builds.

## CD

The intended flow is:

```text
Pull Request approved
-> merge to main
-> GitHub Actions CI
-> build production images
-> deploy staging
-> GitHub Environment approval
-> deploy production
```

`cd.yml` currently contains deployment contracts. Real AWS deployment should be enabled after ECR, ECS service names, Terraform state and GitHub OIDC roles are configured.

`terraform-plan.yml` is a manual staging-only planning workflow. It requires the
GitHub `staging` environment variables documented in `infra/README.md` and does
not run `terraform apply`.

The staging plan workflow uses the S3/DynamoDB remote backend created by
`infra/bootstrap/state`. Bootstrap must happen before the first real plan.

`publish-staging-images.yml` is a manual staging-only image publication
workflow. It resolves the selected Git ref to an exact commit SHA, requires a
successful completed CI run for that SHA, assumes the staging AWS role through
GitHub OIDC, and publishes immutable API/web images to ECR using the commit SHA
as the tag. It is idempotent: if an image tag already exists in ECR, the workflow
reuses it instead of trying to overwrite an immutable tag.

The staging web image is built with `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, because
Next.js public environment values can be compiled into client bundles.

After staging infrastructure exists, deploy only the exact image refs emitted by
the image publication workflow. Do not promote `latest` or locally built images.

`staging-migrations.yml` and `staging-smoke.yml` are manual staging operations.
Use them after the runtime exists to run Alembic as a one-off ECS task and verify
the API/web load balancer paths. Follow `docs/runbooks/staging-operations.md`.

## Recommended Repository Settings

- Require pull requests before merging to `main`.
- Require CI to pass before merging.
- Require linear history.
- Require conversation resolution.
- Require signed commits later when the team is ready.
- Create GitHub Environments:
  - `staging`
  - `production` with required reviewers.
- Configure staging environment variables for Terraform planning before running
  the manual plan workflow.
- Configure staging image publication variables before running the manual image
  publication workflow.
- Configure staging operations variables before running staging migrations or
  smoke checks.
- Enable Dependabot alerts and security updates.
- Use labels:
  - `bug`
  - `enhancement`
  - `security`
  - `meta`
  - `frontend`
  - `backend`
  - `infra`
  - `quality`
  - `release`
  - `triage`

## Dependency Updates

Dependabot runs weekly for the web app, API and GitHub Actions. Minor and patch
updates are grouped by ecosystem and dependency type to keep dependency
maintenance reviewable. Major updates remain separate so breaking changes can be
tested and rolled out intentionally.

## Release Process

1. Merge a tested PR to `main`.
2. Let CI and staging deployment complete.
3. Validate staging manually.
4. Approve production environment deployment.
5. Create a GitHub Release with:
   - user-facing changes
   - migrations
   - rollback notes
   - known risks
