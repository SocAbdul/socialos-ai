# Staging security checklist

Complete before any public staging exposure:

- [ ] Stable domain and TLS are approved; HTTP redirects to HTTPS.
- [ ] Only Caddy publishes ports; PostgreSQL, Redis, API and worker are private.
- [ ] SSH uses keys, non-root user and an IP-restricted firewall rule.
- [ ] `AUTH_MODE=clerk`, demo mode is false and development auth is rejected.
- [ ] `TRUSTED_HOSTS` and CORS contain only the public host plus documented internal health hosts.
- [ ] All secrets are randomly generated, host-only and absent from Git/logs.
- [ ] R2 token is bucket-scoped; bucket listing/public write are disabled.
- [ ] Images use the reviewed immutable `RELEASE_SHA`; health reports the same SHA.
- [ ] Alembic migration and rollback compatibility were reviewed.
- [ ] Encrypted backup, checksum, off-host copy and timed restore drill succeeded.
- [ ] Docker logs rotate; disk/inode thresholds and incident owner are recorded.
- [ ] Meta and all planned providers remain disabled unless separately approved.
- [ ] Smoke test passes without exposing secrets or making a real publication.

Passing this checklist authorizes neither provisioning nor deployment by itself.
