# PostgreSQL staging backup and restore

## Policy

Target RPO is 24 hours and target RTO is 4 hours. Both are objectives, not claims, until an off-host restore drill is timed. Keep seven daily backups and four weekly backups. The script creates SHA-256 sidecars, supports AES-256 encryption using a host-only passphrase file and never contains a default passphrase.

A backup on the same VM is not durable. After each successful local backup, copy the encrypted artifact and checksum to an approved off-host destination with a separate credential and retention policy. R2 backup storage is not configured by this PR.

## Backup

```bash
export STAGING_ENV_FILE=/opt/socialos/.env.staging
export BACKUP_DIRECTORY=/var/backups/socialos
export BACKUP_ENCRYPTION_PASSPHRASE_FILE=/run/secrets/socialos-backup-passphrase
./scripts/postgres-backup.sh
```

Verify the exit code, checksum, artifact size and off-host copy before migration.

## Restore drill

The restore script refuses any database name not ending in `_restore_drill` and requires explicit confirmation.

```bash
export RESTORE_TARGET_DATABASE=socialos_2026q3_restore_drill
export RESTORE_CONFIRMATION=restore-into-isolated-drill-database
./scripts/postgres-restore-drill.sh /secure/path/daily-socialos-TIMESTAMP.dump.enc
```

Record start/end time, source backup timestamp, row-count spot checks and application read tests. Drop the drill database only after evidence is recorded. Never restore over staging without a separate incident approval.
