#!/usr/bin/env python3
"""Offline validation for a populated staging environment file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REQUIRED = {
    "ENVIRONMENT",
    "RELEASE_SHA",
    "APP_BASE_URL",
    "WEB_BASE_URL",
    "API_BASE_URL",
    "WEB_ORIGINS",
    "TRUSTED_HOSTS",
    "API_IMAGE",
    "WEB_IMAGE",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "REDIS_PASSWORD",
    "REDIS_URL",
    "AUTH_MODE",
    "CLERK_JWKS_URL",
    "CLERK_ISSUER",
    "CLERK_AUTHORIZED_PARTIES",
    "TOKEN_ENCRYPTION_KEY",
    "MEDIA_STORAGE_PROVIDER",
    "S3_MEDIA_BUCKET",
    "S3_MEDIA_REGION",
    "S3_MEDIA_PUBLIC_BASE_URL",
    "S3_ENDPOINT_URL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "SOCIAL_PROVIDER",
    "SOCIAL_PROVIDER_META_ENABLED",
    "AI_PROVIDER",
    "NEXT_PUBLIC_DEMO_MODE",
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
    "CADDY_APP_HOST",
    "CADDY_ACME_EMAIL",
}
HTTPS_KEYS = {
    "APP_BASE_URL",
    "WEB_BASE_URL",
    "API_BASE_URL",
    "CLERK_JWKS_URL",
    "CLERK_ISSUER",
    "S3_MEDIA_PUBLIC_BASE_URL",
    "S3_ENDPOINT_URL",
}
PLACEHOLDER_MARKERS = ("example.com", "changeme", "replace-me", "<", ">")


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {number} is not KEY=VALUE")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate(values: dict[str, str], *, allow_placeholders: bool = False) -> list[str]:
    errors: list[str] = []
    missing = sorted(key for key in REQUIRED if not values.get(key))
    if missing and not allow_placeholders:
        errors.append(f"missing or empty variables: {', '.join(missing)}")

    if values.get("ENVIRONMENT") != "staging":
        errors.append("ENVIRONMENT must be staging")
    if values.get("AUTH_MODE") != "clerk":
        errors.append("AUTH_MODE must be clerk")
    if values.get("MEDIA_STORAGE_PROVIDER") != "s3":
        errors.append("MEDIA_STORAGE_PROVIDER must be s3")
    if values.get("SOCIAL_PROVIDER") != "meta":
        errors.append("SOCIAL_PROVIDER must be meta")
    if values.get("NEXT_PUBLIC_DEMO_MODE", "").lower() != "false":
        errors.append("NEXT_PUBLIC_DEMO_MODE must be false")

    release_sha = values.get("RELEASE_SHA", "")
    if release_sha and not re.fullmatch(r"[0-9a-f]{40}", release_sha):
        errors.append("RELEASE_SHA must be a 40-character lowercase Git SHA")

    for key in HTTPS_KEYS:
        value = values.get(key, "")
        if value and urlsplit(value).scheme != "https":
            errors.append(f"{key} must use HTTPS")

    app_origin = values.get("APP_BASE_URL", "").rstrip("/")
    if values.get("WEB_BASE_URL", "").rstrip("/") != app_origin:
        errors.append("WEB_BASE_URL must equal APP_BASE_URL for single-origin staging")
    if values.get("WEB_ORIGINS", "").rstrip("/") != app_origin:
        errors.append("WEB_ORIGINS must contain only APP_BASE_URL for initial staging")
    if values.get("CLERK_AUTHORIZED_PARTIES", "").rstrip("/") != app_origin:
        errors.append("CLERK_AUTHORIZED_PARTIES must equal APP_BASE_URL")

    app_host = urlsplit(app_origin).hostname
    if app_host and values.get("CADDY_APP_HOST") != app_host:
        errors.append("CADDY_APP_HOST must match the APP_BASE_URL hostname")
    trusted_hosts = {item.strip() for item in values.get("TRUSTED_HOSTS", "").split(",")}
    required_hosts = {app_host, "api", "localhost", "127.0.0.1"}
    if app_host and trusted_hosts != required_hosts:
        errors.append("TRUSTED_HOSTS must contain the staging hostname and required internal hosts")

    for provider in ("LINKEDIN", "YOUTUBE", "TIKTOK", "REDDIT"):
        if values.get(f"SOCIAL_PROVIDER_{provider}_ENABLED", "false").lower() != "false":
            errors.append(f"SOCIAL_PROVIDER_{provider}_ENABLED must remain false in initial staging")

    for key in ("API_IMAGE", "WEB_IMAGE"):
        image = values.get(key, "")
        if image.endswith(":latest") or "@latest" in image:
            errors.append(f"{key} must not use latest")

    database_url = values.get("DATABASE_URL", "")
    if database_url and not database_url.startswith("postgresql+asyncpg://"):
        errors.append("DATABASE_URL must use postgresql+asyncpg")
    redis_url = values.get("REDIS_URL", "")
    if redis_url and not redis_url.startswith(("redis://", "rediss://")):
        errors.append("REDIS_URL must use redis or rediss")
    if database_url and "@postgres:5432/" not in database_url:
        errors.append("DATABASE_URL must target private service postgres:5432")
    if redis_url and "@redis:6379/" not in redis_url:
        errors.append("REDIS_URL must target private service redis:6379")

    if values.get("SOCIAL_PROVIDER_META_ENABLED", "").lower() == "true":
        for key in ("META_APP_ID", "META_APP_SECRET", "META_LOGIN_CONFIG_ID", "META_REDIRECT_URI"):
            if not values.get(key):
                errors.append(f"{key} is required when Meta is enabled")
        callback = values.get("META_REDIRECT_URI", "")
        if callback and callback != f"{app_origin}/integrations/meta/callback":
            errors.append("META_REDIRECT_URI must be the stable same-origin callback")

    if not allow_placeholders:
        for key, value in values.items():
            lowered = value.lower()
            if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
                errors.append(f"{key} still contains a placeholder")
        if len(values.get("TOKEN_ENCRYPTION_KEY", "")) < 32:
            errors.append("TOKEN_ENCRYPTION_KEY must contain at least 32 characters")
        if values.get("POSTGRES_PASSWORD") in {"postgres", "socialos", "password"}:
            errors.append("POSTGRES_PASSWORD must not be a default password")
        if values.get("REDIS_PASSWORD") in {"redis", "socialos", "password"}:
            errors.append("REDIS_PASSWORD must not be a default password")

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--allow-placeholders", action="store_true")
    args = parser.parse_args()
    try:
        values = parse_env(args.env_file)
    except (OSError, ValueError) as exc:
        print(f"staging preflight failed: {exc}", file=sys.stderr)
        return 2
    errors = validate(values, allow_placeholders=args.allow_placeholders)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("staging preflight passed (offline; no provider contacted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
