# GitHub Workflow

## Branching

- `main` is protected and deployable.
- Feature work uses `feature/<short-name>` or `agent/<short-name>`.
- Pull requests are opened as drafts until validation is complete.

## CI

Every pull request runs:

- Backend lint, format check, typecheck, migrations and tests.
- Frontend lint, typecheck, unit tests, build and Playwright demo flow.
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

## Recommended Repository Settings

- Require pull requests before merging to `main`.
- Require CI to pass before merging.
- Require linear history.
- Require conversation resolution.
- Require signed commits later when the team is ready.
- Create GitHub Environments:
  - `staging`
  - `production` with required reviewers.
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
