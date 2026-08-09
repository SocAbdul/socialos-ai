import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

from staging_preflight import parse_env, validate  # type: ignore[import-not-found]  # noqa: E402


def valid_values() -> dict[str, str]:
    values = parse_env(ROOT / ".env.staging.example")
    values.update(
        {
            "CADDY_ACME_EMAIL": "ops@example.test",
            "POSTGRES_PASSWORD": "strong-postgres-value",
            "DATABASE_URL": "postgresql+asyncpg://socialos:secret@postgres:5432/socialos",
            "REDIS_PASSWORD": "strong-redis-value",
            "REDIS_URL": "redis://:secret@redis:6379/0",
            "CLERK_JWKS_URL": "https://clerk.test/.well-known/jwks.json",
            "CLERK_ISSUER": "https://clerk.test",
            "TOKEN_ENCRYPTION_KEY": "x" * 48,
            "S3_MEDIA_BUCKET": "staging-media",
            "S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
            "AWS_ACCESS_KEY_ID": "access-key",
            "AWS_SECRET_ACCESS_KEY": "secret-key",
            "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": "pk_test_value",
            "API_IMAGE": "ghcr.io/example/api",
            "WEB_IMAGE": "ghcr.io/example/web",
            "APP_BASE_URL": "https://staging.test",
            "WEB_BASE_URL": "https://staging.test",
            "API_BASE_URL": "https://staging.test/api/v1",
            "WEB_ORIGINS": "https://staging.test",
            "CLERK_AUTHORIZED_PARTIES": "https://staging.test",
            "TRUSTED_HOSTS": "staging.test,api,localhost,127.0.0.1",
            "CADDY_APP_HOST": "staging.test",
            "S3_MEDIA_PUBLIC_BASE_URL": "https://media.staging.test",
            "MEDIA_PUBLIC_BASE_URL": "https://media.staging.test",
            "META_REDIRECT_URI": "https://staging.test/integrations/meta/callback",
        }
    )
    return dict(values)


def test_staging_preflight_accepts_complete_single_origin_configuration() -> None:
    assert validate(valid_values()) == []


def test_staging_preflight_rejects_external_database_and_mutable_image() -> None:
    values = valid_values()
    values["DATABASE_URL"] = "postgresql+asyncpg://user:secret@db.example.test:5432/socialos"
    values["API_IMAGE"] = "ghcr.io/example/api:latest"

    errors = validate(values)

    assert "DATABASE_URL must target private service postgres:5432" in errors
    assert "API_IMAGE must not use latest" in errors
