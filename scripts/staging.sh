#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="${repo_root}/docker-compose.staging.yml"
env_file="${STAGING_ENV_FILE:-${repo_root}/.env.staging}"
export STAGING_ENV_FILE="${env_file}"

usage() {
  echo "Usage: scripts/staging.sh {prepare|migrate|deploy|health|rollback|status}"
}

require_env() {
  [[ -f "${env_file}" ]] || { echo "Missing ignored staging env: ${env_file}" >&2; exit 2; }
  python3 "${repo_root}/scripts/staging_preflight.py" --env-file "${env_file}"
}

compose() {
  docker compose --env-file "${env_file}" -f "${compose_file}" "$@"
}

case "${1:-}" in
  prepare)
    require_env
    docker version >/dev/null
    docker compose version >/dev/null
    compose config --quiet
    echo "Preparation passed. No infrastructure was created."
    ;;
  migrate)
    require_env
    [[ "${MIGRATION_CONFIRMATION:-}" == "run-staging-migration" ]] || {
      echo "Set MIGRATION_CONFIRMATION=run-staging-migration after confirming a backup." >&2
      exit 2
    }
    compose up -d --wait postgres redis
    compose --profile release run --rm migrate
    ;;
  deploy)
    require_env
    [[ "${DEPLOY_CONFIRMATION:-}" == "deploy-existing-staging-host" ]] || {
      echo "Set DEPLOY_CONFIRMATION=deploy-existing-staging-host on an already authorized host." >&2
      exit 2
    }
    compose pull api worker web caddy postgres redis
    compose up -d --wait postgres redis api worker web caddy
    ;;
  health)
    require_env
    app_base_url="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[2]); from staging_preflight import parse_env; print(parse_env(__import__("pathlib").Path(sys.argv[1]))["APP_BASE_URL"])' "${env_file}" "${repo_root}/scripts")"
    release_sha="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[2]); from staging_preflight import parse_env; print(parse_env(__import__("pathlib").Path(sys.argv[1]))["RELEASE_SHA"])' "${env_file}" "${repo_root}/scripts")"
    RELEASE_SHA="${release_sha}" "${repo_root}/scripts/staging-smoke-test.sh" "${app_base_url}"
    compose ps
    ;;
  rollback)
    require_env
    [[ -n "${ROLLBACK_RELEASE_SHA:-}" && "${ROLLBACK_RELEASE_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
      echo "Set ROLLBACK_RELEASE_SHA to a reviewed 40-character Git SHA." >&2
      exit 2
    }
    RELEASE_SHA="${ROLLBACK_RELEASE_SHA}" compose up -d --no-deps api worker web
    echo "Application images rolled back. Database schema was not downgraded."
    ;;
  status)
    require_env
    compose ps
    docker system df
    df -h
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
