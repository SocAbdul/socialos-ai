# Public beta cutover runbook

This runbook describes the controlled path from a validated staging build to a
small public beta.

It does not authorize production deployment by itself. Use it only after the
public beta readiness checklist is complete and the founder/operator approves
the launch issue.

## Preconditions

- Public beta scope is frozen.
- All launch-critical PRs are merged to `main`.
- GitHub Actions CI is green on the selected launch commit.
- Staging runtime exists and is healthy.
- Meta real-publication flow has been verified with Kinetic Mobiles.
- Legal/support/security contacts are live.
- A rollback target is known and documented.

## Cutover sequence

1. Select the launch commit SHA from `main`.
2. Confirm CI is green for that exact SHA.
3. Publish immutable staging images for that SHA.
4. Update staging runtime image refs to that SHA.
5. Run database migrations as a one-off ECS task if needed.
6. Run staging smoke checks.
7. Manually verify:
   - sign-in;
   - workspace access;
   - Meta connection visibility;
   - media upload;
   - AI adaptation;
   - schedule or publish;
   - publication status and external URL.
8. Record the launch evidence in the launch issue.
9. If production infrastructure is not yet created, stop here and keep staging as
   the private validation environment.
10. If production infrastructure has separately been approved, repeat the same
    immutable-image and migration sequence using production-specific workflows.

## Go/no-go decision

Launch only if:

- all critical checklist items are complete;
- no open P0/P1 bugs exist;
- staging smoke is green;
- rollback is understood;
- expected beta user count is small enough for manual support;
- Meta rate limits and review status are acceptable.

If the decision is no-go, keep the launch issue open and create fix issues for
the blockers.

## First hour after public access

Monitor continuously:

- API health and readiness;
- ECS service stability;
- error logs;
- Meta OAuth callbacks;
- publication attempts;
- retry counts;
- user-reported onboarding friction.

Do not ship unrelated changes during the first hour. If a serious issue appears,
stop new invites and follow the rollback runbook.

## First day after public access

Review:

- number of successful sign-ins;
- number of connected Meta accounts;
- number of successful publications;
- failed publication attempts by reason;
- AI generation failures;
- media upload failures;
- support/security inboxes;
- AWS cost and budget alarms.

Create follow-up issues for every repeated user confusion or operational failure.

## Rollback trigger

Rollback immediately if:

- auth allows cross-workspace access;
- tokens are exposed in logs or UI;
- duplicate real posts are created;
- Meta publication errors cannot be reconciled;
- database migrations corrupt data;
- staging/public API readiness fails persistently;
- AWS cost spikes unexpectedly.

Follow `docs/runbooks/staging-rollback.md` for staging rollback. Production
rollback must use a separate production-approved runbook.
