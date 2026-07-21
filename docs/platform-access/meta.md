# Meta Platform Access

Status: IMPLEMENTED_NOT_VERIFIED.

## Requirements

- Meta developer app with Facebook Login configured.
- A Facebook Page managed by the connecting user.
- For Instagram publishing, an Instagram Business or Creator account connected to that Facebook Page.
- Publicly reachable image/video URLs for media publishing. S3 plus CloudFront is the intended production path.
- Production app review before broad public access.

## OAuth Permissions

Initial publishing slice requests:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`
- `instagram_basic`
- `instagram_content_publish`

The backend exchanges the OAuth code for a user token, exchanges that for a longer-lived token, reads manageable Pages, then stores Page access tokens encrypted per `PlatformConnection`.

## Review Process

Meta permissions used for publishing require App Review for public customer use. Development mode can publish only with app roles/test users and compatible test assets. The production launch checklist must include review screencasts showing account connection, content creation, publishing, error handling, and disconnect/reconnect behavior.

## Compatible Accounts

- Facebook: Pages where the user has sufficient tasks/permissions.
- Instagram: Business or Creator accounts connected to a Facebook Page.
- Personal Instagram accounts are not compatible with this publishing flow.

## Limits

- Instagram Content Publishing has a documented API-published media limit of 100 posts per rolling 24-hour period per account.
- Platform rate limits and Page/app limits must be monitored from Meta responses.
- SocialOS stores provider capabilities in `PlatformConnection.capabilities` and must enforce limits before enqueueing high-volume jobs.

## Content Types

Implemented provider capabilities:

- Facebook Page: text and single image are enabled in this slice.
- Instagram: single image is enabled in this slice; video/Reels capability is declared and provider code path exists, but production rollout should validate upload processing and status polling before exposing at scale.

## Token Renewal

Tokens are encrypted at rest using `TOKEN_ENCRYPTION_KEY`. The provider exposes `refresh_credentials`; production should run a scheduled refresh job before token expiry and mark connections invalid if refresh fails.

## Webhooks

Not implemented yet. Meta webhooks should be added for connection health, comments/engagement, deletion or moderation events, and post-publication status reconciliation.

## Restrictions

- Do not expose access tokens to the frontend.
- Do not treat Meta test-mode success as public-readiness.
- Instagram publishing requires media URLs reachable by Meta.
- Publishing retries must not create duplicates; SocialOS uses a publication `idempotency_key`, persisted external IDs, and terminal-state checks.

## Implementation State

- Neutral `PlatformConnection` model: implemented.
- `SocialAccount` model for Facebook Page and Instagram professional accounts: implemented.
- OAuth URL generation: implemented.
- One-time OAuth state with expiry and workspace/user binding: implemented.
- OAuth callback and account discovery: implemented.
- Encrypted token storage: implemented.
- Facebook Page text/image publishing: implemented.
- Instagram image publishing through media container, `status_code` polling, and publish: implemented.
- Publication attempts/status dashboard API: partially implemented.
- Internal lease/execution-key protection against simultaneous workers: implemented.
- Uncertain result state for timeout/connection ambiguity: implemented.
- Full webhook reconciliation: pending.
- Real Kinetic Mobiles test publication: pending Meta app credentials, compatible account, and approved/testable permissions.

## Delivery Guarantees

SocialOS runs publication jobs with at-least-once delivery. Internally, each job takes a transactional row lock, assigns an `execution_key`, and records a lease timeout before calling Meta. While the lease is active, manual and automatic retries return without publishing again.

The database stores terminal `external_publication_id` values and clears active leases after success. If Meta times out or the worker cannot know whether Meta processed the request, the publication moves to `UNCERTAIN` for reconciliation instead of blindly retrying.

Exactly-once publishing cannot be guaranteed against third-party APIs unless the provider exposes a durable idempotency key or queryable request identity. Meta publishing APIs do not provide a universal exactly-once primitive for this flow, so SocialOS guarantees internal deduplication plus external reconciliation.

## Known Risks

- Meta review can slow launch timing.
- Token and permission behavior differs between development mode, app-role users, and live apps.
- Instagram media processing for video/Reels needs polling before large-scale release.
- External media URLs must be stable, public, and not blocked by CloudFront/S3 policy.
