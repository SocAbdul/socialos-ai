# YouTube platform access

**STATUS: PLANNED**

- Intended official API: YouTube Data API v3.
- Expected access: Google OAuth 2.0 with `youtube.upload` for uploads.
- Future API capabilities: resumable video upload, processing status and deletion. SocialOS currently implements none of them.
- Verification: uploads from unverified API projects can be restricted to private; an audit is required before public uploads are enabled.
- Limits: quota and upload constraints must be read from the current official API before implementation.
- Shorts: planned as a video publishing use case, not declared as a separate implemented API capability.
- Not implemented: Google project, credentials, OAuth, channel discovery, upload, scheduling, status reconciliation, analytics or webhooks.

Official references: https://developers.google.com/youtube/v3/docs/videos/insert and https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
