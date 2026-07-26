from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def hcl_string(value: str) -> str:
    return json.dumps(value)


def hcl_map(values: dict[str, str]) -> str:
    if not values:
        return "{}"
    lines = ["{"]
    for key in sorted(values):
        lines.append(f"  {key} = {hcl_string(values[key])}")
    lines.append("}")
    return "\n".join(lines)


def hcl_list_from_raw(value: str) -> str:
    value = value.strip()
    if not value:
        return "[]"
    if not (value.startswith("[") and value.endswith("]")):
        raise SystemExit("STAGING_SECRET_KMS_KEY_ARNS_HCL must be an HCL list, for example: []")
    return value


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: write_staging_tfvars.py <output-path>")

    output_path = Path(sys.argv[1])
    web_origin = os.environ["STAGING_WEB_ORIGIN"].rstrip("/")

    api_environment = {
        "CLERK_AUTHORIZED_PARTIES": web_origin,
        "CLERK_ISSUER": os.environ["CLERK_ISSUER"],
        "CLERK_JWKS_URL": os.environ["CLERK_JWKS_URL"],
        "META_REDIRECT_URI": f"{web_origin}/integrations/meta/callback",
        "WEB_ORIGINS": web_origin,
    }
    if os.environ.get("CLERK_AUDIENCE"):
        api_environment["CLERK_AUDIENCE"] = os.environ["CLERK_AUDIENCE"]
    if os.environ.get("META_APP_ID"):
        api_environment["META_APP_ID"] = os.environ["META_APP_ID"]

    api_secrets = {
        "TOKEN_ENCRYPTION_KEY": os.environ["TOKEN_ENCRYPTION_KEY_SECRET_ARN"],
    }
    if os.environ.get("META_APP_SECRET_ARN"):
        api_secrets["META_APP_SECRET"] = os.environ["META_APP_SECRET_ARN"]

    existing_oidc = os.environ.get("EXISTING_GITHUB_OIDC_PROVIDER_ARN", "").strip()
    existing_oidc_hcl = hcl_string(existing_oidc) if existing_oidc else "null"
    enable_runtime = os.environ.get("ENABLE_STAGING_RUNTIME", "false").lower() == "true"

    contents = f"""aws_region = {hcl_string(os.environ["AWS_REGION"])}
media_bucket_name = {hcl_string(os.environ["S3_MEDIA_BUCKET"])}
media_cors_allowed_origins = [{hcl_string(web_origin)}]
monthly_budget_limit_usd = {os.environ["MONTHLY_BUDGET_LIMIT_USD"]}
budget_alert_email = {hcl_string(os.environ["BUDGET_ALERT_EMAIL"])}
github_repository = {hcl_string(os.environ["GITHUB_REPOSITORY"])}
existing_github_oidc_provider_arn = {existing_oidc_hcl}

enable_staging_runtime = {str(enable_runtime).lower()}
staging_api_image = {hcl_string(os.environ.get("STAGING_API_IMAGE") or "REPLACE_AFTER_STAGING_IMAGE_PUBLICATION")}
staging_web_image = {hcl_string(os.environ.get("STAGING_WEB_IMAGE") or "REPLACE_AFTER_STAGING_IMAGE_PUBLICATION")}
staging_desired_count = {os.environ.get("STAGING_DESIRED_COUNT") or "1"}

staging_api_environment = {hcl_map(api_environment)}
staging_web_environment = {hcl_map({
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": os.environ["NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"],
})}

staging_api_secret_arns = {hcl_map(api_secrets)}
staging_web_secret_arns = {hcl_map({
    "CLERK_SECRET_KEY": os.environ["CLERK_SECRET_KEY_SECRET_ARN"],
})}
staging_secret_kms_key_arns = {hcl_list_from_raw(os.environ.get("STAGING_SECRET_KMS_KEY_ARNS_HCL", ""))}
"""
    output_path.write_text(contents)


if __name__ == "__main__":
    main()
