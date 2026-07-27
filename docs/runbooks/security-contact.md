# Security contact runbook

SocialOS AI exposes `/.well-known/security.txt` so security researchers and
operators have an obvious responsible-disclosure path.

## Current contacts

- `security@socialos.ai`
- `support@socialos.ai`

These mailboxes must exist before any public launch or public beta traffic.

## Before public launch

Verify:

- the security mailbox exists and is monitored;
- at least two founders/operators can access or receive alerts from it;
- inbound messages are not filtered to spam;
- the canonical security policy page exists if `https://socialos.ai/security`
  is advertised publicly;
- the incident response owner knows how to create a private GitHub security
  advisory or internal issue without exposing sensitive reports.

## Handling reports

1. Acknowledge receipt without asking the reporter to disclose secrets publicly.
2. Create a private issue/advisory with the reporter, affected area and severity.
3. Reproduce safely in local or staging environments.
4. Patch in a private branch if the issue is exploitable.
5. Backport or deploy according to severity.
6. Credit the reporter only if they ask for credit and disclosure is safe.

Do not request production credentials, customer tokens or destructive proof from
external reporters.
