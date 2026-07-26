# GitHub Workflow

## Branching

- `main` is protected and deployable.
- Feature work uses `feature/<short-name>` or `agent/<short-name>`.
- Pull requests are opened as drafts until validation is complete.

## CI

Every pull request runs:

- Backend lint, format check, typecheck, migrations and tests.
- Frontend lint, typecheck, unit tests, build and Playwright demo flow.
- Terraform format and validation for infrastructure environments.
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

`publish-staging-images.yml` is a manual staging-only image publication
workflow. It resolves the selected Git ref to an exact commit SHA, requires a
successful completed CI run for that SHA, assumes the staging AWS role through
GitHub OIDC, and publishes immutable API/web images to ECR using the commit SHA
as the tag. It is idempotent: if an image tag already exists in ECR, the workflow
reuses it instead of trying to overwrite an immutable tag.

After staging infrastructure exists, deploy only the exact image refs emitted by
the image publication workflow. Do not promote `latest` or locally built images.

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
- Enable Dependabot alerts and security updates.
- Use labels:
  - `bug`
  - `feature`
  - `security`
  - `meta`
  - `frontend`
  - `backend`
  - `infra`
  - `triage`

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
