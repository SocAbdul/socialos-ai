# Meta Platform Access

Status: VERIFIED_IN_DEVELOPMENT.

## Requirements

- Meta developer app in Development/Unpublished mode with Facebook Login for Business configured.
- A combined Facebook Login for Business configuration supplied only through `META_LOGIN_CONFIG_ID`; its identifier must never be committed.
- A Facebook Page managed by the connecting user.
- For Instagram publishing, an Instagram Business or Creator account connected to that Facebook Page.
- Publicly reachable image/video URLs for media publishing. S3 plus CloudFront is the intended production path.
- Production app review before broad public access.

## OAuth Permissions

Initial publishing slice requests:

- `business_management`
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`
- `instagram_basic`
- `instagram_content_publish`

These six permissions are fixed in the Meta configuration. SocialOS sends `config_id` and deliberately does not send a `scope` override. Meta redirects the browser to the configured frontend callback route. The
authenticated frontend posts the returned OAuth `code` and `state` to the
backend, which exchanges the code for a user token, exchanges that for a
longer-lived token, reads manageable Pages, then stores Page access tokens
encrypted per `PlatformConnection`.

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
- Instagram: single image only.
- Video, Reels, Stories, carousels and Facebook video are not exposed.

## Token Renewal

Tokens are encrypted at rest using `TOKEN_ENCRYPTION_KEY`. Scheduled Meta credential renewal remains pending: `refresh_credentials` fails explicitly instead of attempting to exchange a Page token or risking loss of the encrypted user token. A future renewal workflow must receive the target connection, renew the user token, enumerate `/me/accounts`, and persist both refreshed tokens.

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
- OAuth URL generation with Facebook Login for Business `config_id`: implemented, not verified against Meta.
- One-time OAuth state with expiry and workspace/user binding: implemented.
- Temporary encrypted OAuth selection sessions, safe candidates and one-use row-locked selection: implemented.
- Reconnect sessions are bound to the original `PlatformConnection`; selecting a different Page is rejected.
- Shared Page authorization with Facebook and linked Instagram represented as `SocialAccount` records: implemented.
- Connection validation rechecks the user token, six permissions, Page visibility, Page token, publishing tasks and linked professional Instagram account. Removed or changed accounts are deactivated without deleting history.
- OAuth callback and account discovery: implemented with mocked tests only.
- Encrypted token storage: implemented.
- Facebook Page text/image publishing: implemented.
- Instagram image publishing through media container, `status_code` polling, and publish: implemented.
- Publication attempts/status dashboard API: partially implemented.
- Internal lease/execution-key protection against simultaneous workers: implemented.
- Uncertain result state for timeout/connection ambiguity: implemented.
- Full webhook reconciliation: pending.
- Real Kinetic Mobiles authorization and publication: verified in Meta Development mode on
  2026-08-07. One Facebook Page image post and one Instagram professional image post
  completed through the official API with `started -> succeeded` attempt histories and
  externally reachable result URLs.
- Public customer authorization remains blocked on Meta App Review and Live mode.

## Local configuration runbook

Set these values only in the local environment or an approved secret store:

```dotenv
SOCIAL_PROVIDER=meta
META_APP_ID=
META_APP_SECRET=
META_LOGIN_CONFIG_ID=
META_REDIRECT_URI=http://localhost:3000/integrations/meta/callback
META_GRAPH_API_VERSION=v25.0
```

Meta's current setup UI may display Graph API v26. Keep the API version configurable and retain v25 until a supervised real validation explicitly approves changing it. The OAuth success path supports full-page redirect universally; a desktop popup is only an enhancement and falls back to the same-window flow.

Disconnecting normally means “Disconnect from SocialOS”: local credentials are made unusable, accounts are deactivated and history is preserved. It does not revoke the entire authorization in Meta.

## Delivery Guarantees

SocialOS runs publication jobs with at-least-once delivery. Internally, each job takes a transactional row lock, assigns an `execution_key`, and records a lease timeout before calling Meta. While the lease is active, manual and automatic retries return without publishing again.

The database stores terminal `external_publication_id` values and clears active leases after success. If Meta times out or the worker cannot know whether Meta processed the request, the publication moves to `UNCERTAIN` for reconciliation instead of blindly retrying.

Exactly-once publishing cannot be guaranteed against third-party APIs unless the provider exposes a durable idempotency key or queryable request identity. Meta publishing APIs do not provide a universal exactly-once primitive for this flow, so SocialOS guarantees internal deduplication plus external reconciliation.

## Known Risks

- Meta review can slow launch timing.
- Token and permission behavior differs between development mode, app-role users, and live apps.
- Instagram media processing for video/Reels needs polling before large-scale release.
- External media URLs must be stable, public, and not blocked by CloudFront/S3 policy.
