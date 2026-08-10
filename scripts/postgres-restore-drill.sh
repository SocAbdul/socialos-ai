#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${STAGING_ENV_FILE:-${repo_root}/.env.staging}"
source_backup="${1:-}"
target_db="${RESTORE_TARGET_DATABASE:-socialos_restore_drill}"

[[ -f "${source_backup}" ]] || { echo "Usage: scripts/postgres-restore-drill.sh BACKUP" >&2; exit 2; }
[[ "${target_db}" =~ _restore_drill$ ]] || { echo "Target database must end in _restore_drill." >&2; exit 2; }
[[ "${RESTORE_CONFIRMATION:-}" == "restore-into-isolated-drill-database" ]] || {
  echo "Set RESTORE_CONFIRMATION=restore-into-isolated-drill-database." >&2
  exit 2
}

temporary=""
cleanup() { [[ -z "${temporary}" ]] || rm -f -- "${temporary}"; }
trap cleanup EXIT
restore_file="${source_backup}"
if [[ "${source_backup}" == *.enc ]]; then
  [[ -r "${BACKUP_ENCRYPTION_PASSPHRASE_FILE:-}" ]] || { echo "Passphrase file required." >&2; exit 2; }
  temporary="$(mktemp)"
  openssl enc -d -aes-256-cbc -pbkdf2 \
    -pass "file:${BACKUP_ENCRYPTION_PASSPHRASE_FILE}" \
    -in "${source_backup}" -out "${temporary}"
  restore_file="${temporary}"
fi

compose=(docker compose --env-file "${env_file}" -f "${repo_root}/docker-compose.staging.yml")
"${compose[@]}" exec -T -e RESTORE_TARGET_DATABASE="${target_db}" postgres sh -ec \
  'dropdb -U "$POSTGRES_USER" --if-exists "$RESTORE_TARGET_DATABASE" && createdb -U "$POSTGRES_USER" "$RESTORE_TARGET_DATABASE"'
"${compose[@]}" exec -T -e RESTORE_TARGET_DATABASE="${target_db}" postgres sh -ec \
  'pg_restore -U "$POSTGRES_USER" -d "$RESTORE_TARGET_DATABASE" --no-owner' <"${restore_file}"
"${compose[@]}" exec -T -e RESTORE_TARGET_DATABASE="${target_db}" postgres sh -ec \
  'psql -U "$POSTGRES_USER" -d "$RESTORE_TARGET_DATABASE" -v ON_ERROR_STOP=1 -c "SELECT 1;"'
echo "Restore drill completed into isolated database ${target_db}; RPO/RTO remain unverified until timings are recorded."
