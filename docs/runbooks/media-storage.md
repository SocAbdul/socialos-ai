# Media storage runbook

SocialOS AI must never proxy user media through the API in production. The API
issues short-lived upload targets, the browser uploads directly to object
storage, and only the stable public media URL is stored on `MediaAsset`.

## Local development

The zero-cost local preview uses:

```env
MEDIA_STORAGE_PROVIDER=local-public
LOCAL_MEDIA_ROOT=/data/public-media
LOCAL_MEDIA_HOST_PATH=./.data/public-media
MEDIA_PUBLIC_BASE_URL=https://<current-protected-preview-host>/media
```

The dashboard accepts JPEG/PNG files, the API verifies their bytes and writes them
under an opaque random key in the persistent host mount. PostgreSQL stores only
the key, checksum, MIME, size and public URL. Configure the reverse proxy to expose
only `/media/*` without Basic Auth; dashboard and API routes remain protected.

`MEDIA_STORAGE_PROVIDER=local` remains a non-uploading legacy contract used by
isolated tests. It must not be used for the real local composer.

## Staging and production

Use:

```env
MEDIA_STORAGE_PROVIDER=s3
MEDIA_UPLOAD_URL_TTL_SECONDS=900
MEDIA_MAX_UPLOAD_BYTES=15728640
S3_MEDIA_BUCKET=socialos-ai-media-...
S3_MEDIA_REGION=...
S3_MEDIA_PUBLIC_BASE_URL=https://media.socialos.ai
```

`S3_MEDIA_PUBLIC_BASE_URL` should point at CloudFront, not directly at a private
S3 bucket. The CloudFront origin must be allowed to read the media objects.

In ECS, the API must sign S3 upload URLs through its task role. Do not configure
static `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in staging or production.
Local development may still use the standard AWS credential chain when testing
S3 manually.

Terraform for the staging media foundation lives in
`infra/environments/staging`. It creates:

- private S3 bucket;
- KMS encryption;
- CORS for browser direct uploads;
- CloudFront distribution with Origin Access Control;
- bucket policy allowing CloudFront reads;
- least-privilege media signer IAM policy for the API runtime identity.

Run `terraform plan` first and do not apply until AWS account, state backend,
budget alarms and staging DNS are approved.

## Upload flow

For `local-public`, the client sends multipart data to
`POST /api/v1/workspaces/{workspace_id}/media-assets/upload`. The API validates
the actual signature, extension, MIME and size, persists the file and registers
the `MediaAsset` in one operation.

For S3 deployments:

1. Client calls `POST /api/v1/workspaces/{workspace_id}/media-assets/upload-target`.
2. API verifies workspace access, content type, size and checksum format.
3. API returns:
   - `upload_url`: short-lived signed PUT URL.
   - `public_url`: stable URL stored later on `MediaAsset`.
   - `headers`: required upload headers.
   - `expires_at`: upload target expiry.
4. Client uploads the binary directly with `PUT`.
5. Client calls `POST /api/v1/workspaces/{workspace_id}/media-assets` with:
   - `storage_url` = returned `public_url`.
   - `checksum_sha256` = original SHA-256 digest.
   - `content_type` and `media_type`.
6. Publications reference the registered `MediaAsset`.

## Security rules

- Do not log `upload_url`.
- Do not store `upload_url`.
- Do not expose AWS credentials to the frontend.
- Prefer ECS task roles/OIDC-assumed roles over static IAM user access keys.
- Keep upload TTL short.
- Keep media bucket write access limited to the API signer identity.
- Use separate buckets or prefixes per environment.
- Configure S3 lifecycle policies for deleted/abandoned media.

## Meta-specific constraints

Meta must be able to fetch the `public_url` over HTTPS. Before real publishing,
verify:

- CloudFront URL returns `200` without cookies or auth headers.
- Content-Type is correct.
- Image/video size is within Meta platform limits.
- The URL remains stable while Meta creates and publishes the media container.
