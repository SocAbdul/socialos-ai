# Security Policy

## Reporting Security Issues

Do not open public issues for vulnerabilities. Report privately to the project owner until a private security advisory process is configured.

## Secret Handling

Never commit:

- `.env` files
- API keys
- Meta app secrets
- OAuth authorization codes
- access or refresh tokens
- signed media URLs
- production database URLs

## Current Security Baseline

- Clerk JWT verification is fail-closed outside development.
- Meta tokens are encrypted at rest.
- Social publication jobs use transactional locks, leases and execution keys.
- Demo mode is isolated from real provider adapters.

## Required Before Production

- Configure GitHub branch protection.
- Configure GitHub environments for staging and production approvals.
- Configure cloud secrets through GitHub Actions environments or AWS Secrets Manager.
- Complete dependency scanning and vulnerability triage.
- Complete a focused security review of OAuth and publishing flows.
