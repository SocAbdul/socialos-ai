# Infrastructure

Terraform is separated into reusable modules and environment compositions.
Remote state, AWS account IDs, DNS zones, and secrets are environment-owned and
must never be committed.

The initial module creates the secure artifact layer used by every environment:

- private, versioned S3 media bucket;
- public access fully blocked;
- KMS-backed server-side encryption;
- lifecycle rules for incomplete multipart uploads;
- CloudFront origin access control.

ECS, RDS, ElastiCache, networking, WAF, observability, and deployment roles will
be added as independent modules after the AWS account and environment topology
are confirmed.

