# Media storage runbook

SocialOS AI must never proxy user media through the API in production. The API
issues short-lived upload targets, the browser uploads directly to object
storage, and only the stable public media URL is stored on `MediaAsset`.

## Local development

Use:

```env
MEDIA_STORAGE_PROVIDER=local
```

The API returns a non-uploading local contract target so clients can exercise the
same shape without AWS credentials.

## Staging and production

Use:

```env
MEDIA_STORAGE_PROVIDER=s3
MEDIA_UPLOAD_URL_TTL_SECONDS=900
MEDIA_MAX_UPLOAD_BYTES=15728640
S3_MEDIA_BUCKET=socialos-ai-media-...
S3_MEDIA_REGION=...
S3_MEDIA_PUBLIC_BASE_URL=https://media.socialos.ai
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=
```

`S3_MEDIA_PUBLIC_BASE_URL` should point at CloudFront, not directly at a private
S3 bucket. The CloudFront origin must be allowed to read the media objects.

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
