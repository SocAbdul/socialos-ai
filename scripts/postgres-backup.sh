#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${STAGING_ENV_FILE:-${repo_root}/.env.staging}"
backup_dir="${BACKUP_DIRECTORY:-/var/backups/socialos}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
plain_backup="${backup_dir}/daily-socialos-${timestamp}.dump"

[[ -f "${env_file}" ]] || { echo "Missing env file: ${env_file}" >&2; exit 2; }
mkdir -p "${backup_dir}"
umask 077

docker compose --env-file "${env_file}" -f "${repo_root}/docker-compose.staging.yml" \
  exec -T postgres sh -ec \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --file=-' \
  >"${plain_backup}"

backup_path="${plain_backup}"
if [[ -n "${BACKUP_ENCRYPTION_PASSPHRASE_FILE:-}" ]]; then
  [[ -r "${BACKUP_ENCRYPTION_PASSPHRASE_FILE}" ]] || { echo "Encryption passphrase file is unreadable." >&2; exit 2; }
  openssl enc -aes-256-cbc -pbkdf2 -salt \
    -pass "file:${BACKUP_ENCRYPTION_PASSPHRASE_FILE}" \
    -in "${plain_backup}" -out "${plain_backup}.enc"
  rm -f -- "${plain_backup}"
  backup_path="${plain_backup}.enc"
fi

sha256sum "${backup_path}" >"${backup_path}.sha256"
if [[ "$(date -u +%u)" == "7" ]]; then
  weekly_path="${backup_dir}/weekly-$(basename "${backup_path#${backup_dir}/}")"
  cp -- "${backup_path}" "${weekly_path}"
  sha256sum "${weekly_path}" >"${weekly_path}.sha256"
fi
find "${backup_dir}" -maxdepth 1 -type f -name 'daily-socialos-*.dump*' -mtime +7 -delete
find "${backup_dir}" -maxdepth 1 -type f -name 'weekly-*.dump*' -mtime +28 -delete
echo "Backup created locally: ${backup_path}"
echo "OFF-HOST COPY REQUIRED: this script does not claim the backup is durable until export and restore succeed."
