# Release and rollback

1. Select the exact Git SHA and require green CI.
2. Build immutable `socialos-api:<git-sha>` and `socialos-web:<git-sha>` images.
3. Confirm database and object-storage backup status; current RPO/RTO remain **TBD** until a hosting decision is approved.
4. Run one migration job with the new API image.
5. Roll out API, worker and web using the same tested SHA.
6. Verify readiness, worker broker connectivity, web health and a tenant-isolated smoke test.
7. Monitor structured logs using `request_id`, `publication_id` and attempt identifiers.
8. Roll back application images if health or smoke tests fail. Do not blindly downgrade a migrated schema.

PostgreSQL backups must include schema and data and be restore-tested. Object-storage backups/versioning must cover original media objects and metadata. A backup is not considered operational until a restore exercise succeeds.
