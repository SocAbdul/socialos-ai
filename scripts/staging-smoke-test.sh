#!/usr/bin/env bash
set -Eeuo pipefail

base_url="${1:-${APP_BASE_URL:-}}"
[[ "${base_url}" == https://* ]] || { echo "A stable HTTPS APP_BASE_URL is required." >&2; exit 2; }

curl --fail --silent --show-error --location --max-time 15 "${base_url}/" >/dev/null
live="$(curl --fail --silent --show-error --max-time 15 "${base_url}/health/live")"
ready="$(curl --fail --silent --show-error --max-time 15 "${base_url}/health/ready")"

python3 - "${live}" "${ready}" "${RELEASE_SHA:-}" <<'PY'
import json
import sys

live = json.loads(sys.argv[1])
ready = json.loads(sys.argv[2])
expected_release = sys.argv[3]
assert live["status"] == "ok", live
assert ready["status"] == "ready", ready
assert ready["dependencies"]["database"]["status"] == "ok", ready
assert ready["dependencies"]["redis"]["status"] == "ok", ready
if expected_release:
    assert ready["release_sha"] == expected_release, ready
PY

echo "staging smoke passed; no OAuth or social publication was attempted"
