# Security contact runbook

SocialOS AI exposes `/.well-known/security.txt` so security researchers and
operators have an obvious responsible-disclosure path.

## Current reporting path

Use GitHub Security Advisories:

https://github.com/SocAbdul/socialos-ai/security/advisories/new

Do not advertise project-owned email addresses until the mailboxes exist and are
monitored.

## Before public launch

Verify:

- the security mailbox exists and is monitored;
- at least two founders/operators can access or receive alerts from it;
- inbound messages are not filtered to spam;
- a canonical security policy page exists before any custom-domain canonical URL
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
