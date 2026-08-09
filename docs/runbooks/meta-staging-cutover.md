# Meta staging cutover

Status: not executed. Meta stays disabled until every prerequisite is approved.

1. Establish a stable HTTPS staging hostname and verify single-origin routing.
2. Add exactly `https://<staging-host>/integrations/meta/callback` to the existing Meta configuration manually.
3. Populate Meta identifiers and secret only in the ignored host environment, then enable `SOCIAL_PROVIDER_META_ENABLED=true`.
4. Run the offline preflight and restart API/worker. Never print the environment or tokens.
5. Use a dedicated non-customer test Page and linked professional Instagram account.
6. Verify OAuth session isolation, selection, validation, disconnect/reconnect and publication guards before the first test publication.
7. Publish only after separate explicit authorization, then reconcile external URL/status and audit events.

Rollback is to disable Meta, restart API/worker and invalidate local connections. Do not automatically revoke the entire Meta authorization. Any callback or domain change requires a new reviewed cutover.
