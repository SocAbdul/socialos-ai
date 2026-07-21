# Meta Real Publication Runbook

Integration status: IMPLEMENTED_NOT_VERIFIED.

This runbook must be completed before marking Meta as `VERIFIED_IN_DEVELOPMENT`, `VERIFIED_IN_STAGING`, or `PRODUCTION_READY`.

## 1. Meta App Setup

1. Create or open the Meta developer app for SocialOS AI.
2. Configure Facebook Login for Business.
3. Set the OAuth redirect URI exactly to `META_REDIRECT_URI`.
4. Add development/test users who can manage Kinetic Mobiles assets.
5. Confirm Kinetic Mobiles has a Facebook Page.
6. Confirm Kinetic Mobiles has an Instagram Business or Creator account connected to that Page.

## 2. Environment

Set these variables outside chat, in `.env` or deployment secrets:

```env
TOKEN_ENCRYPTION_KEY=long-random-secret
META_APP_ID=...
META_APP_SECRET=...
META_REDIRECT_URI=http://localhost:8000/api/v1/platform-connections/meta/callback
META_GRAPH_API_VERSION=v25.0
```

Never log or paste `META_APP_SECRET`, authorization codes, access tokens, or signed media URLs.

## 3. Permissions

Request and verify these permissions:

- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`
- `instagram_basic`
- `instagram_content_publish`

For public customer use, complete Meta App Review with a screencast showing connection, account selection, publishing, error handling, retry, disconnect, and reconnect.

## 4. Local Services

After moving the repository to `C:\dev\socialos-ai` and starting Docker Desktop:

```powershell
docker compose up -d postgres redis
cd apps/api
uv run alembic upgrade head
uv run pytest
uv run mypy src tests
uv run ruff check .
```

Then start:

```powershell
docker compose up api worker web
```

For frontend validation in `C:\dev\socialos-ai\apps\web`:

```powershell
npm ci
npm run lint
npm run typecheck
npm run build
```

## 5. Connect Kinetic Mobiles

1. Sign in to SocialOS AI.
2. Create or select the Kinetic Mobiles workspace.
3. Open Meta authorization.
4. Complete OAuth as a user who can manage the Kinetic Mobiles Facebook Page.
5. Confirm SocialOS discovers:
   - Facebook Page account.
   - Instagram Business or Creator account.
6. Confirm tokens are not visible in API responses or logs.

## 6. Publish To Facebook

1. Create a campaign.
2. Create a content item.
3. Register a public media URL if publishing an image.
4. Create a publication against the Facebook Page `SocialAccount`.
5. Publish now.
6. Confirm dashboard status becomes `published`.
7. Open `external_url` and verify the post exists on Facebook.

## 7. Publish To Instagram

1. Use a publicly reachable HTTPS image URL. Do not use localhost.
2. Create a publication against the Instagram professional `SocialAccount`.
3. Confirm SocialOS rejects text-only Instagram publishing before enqueue.
4. Publish now.
5. Confirm the worker creates the container.
6. Confirm container polling reaches `FINISHED`.
7. Confirm `media_publish` returns `external_publication_id`.
8. Open the external result where available and verify the Instagram post.

## 8. Error Simulation

1. Use an invalid image URL and confirm container creation/polling fails safely.
2. Confirm status becomes retryable/permanent/uncertain according to the normalized error.
3. Trigger manual retry while an automatic retry is active.
4. Confirm only one active execution lease exists.
5. Confirm no duplicate Facebook or Instagram post is created.

## 9. Reconnect Flow

1. Disconnect or revoke Meta access.
2. Confirm connection becomes invalid or `reauth_required`.
3. Reconnect through OAuth.
4. Confirm accounts are rediscovered and publication can resume.

## 10. Completion Criteria

Meta can move from `IMPLEMENTED_NOT_VERIFIED` to `VERIFIED_IN_DEVELOPMENT` only after one real Kinetic Mobiles Facebook post and one real Kinetic Mobiles Instagram post are published from SocialOS AI and verified through their external links.
