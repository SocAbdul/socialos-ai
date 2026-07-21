# UI/UX Review Checklist

Use this checklist with `NEXT_PUBLIC_DEMO_MODE=true` at `http://localhost:3000`.

## Core Flow

- Dashboard loads without backend.
- The next action is obvious: create a publication.
- Meta connection is visible and clearly marked as demo/local.
- Facebook Page account is visible.
- Instagram Business account is visible.
- Account capabilities are understandable.
- Composer contains realistic Kinetic Mobiles copy.
- Image upload state is represented without implying a real upload.
- Facebook and Instagram can be selected.
- Adapted copy is different per platform.
- Facebook preview is readable.
- Instagram preview is readable.
- Publish now creates publication records.
- Schedule creates scheduled publication records.
- Publications list shows clear statuses.
- Publication detail explains what to do next.
- Failed publication offers retry.
- Uncertain publication explains reconciliation before retry.
- Retry resolves without implying duplicate posts.
- Reset demo restores original data.

## States

- Empty state explains how to create the first publication.
- Loading state appears before local demo data loads.
- Success message appears after adaptation, publish, schedule and retry.
- Error text is specific and human-readable.
- Status chips are distinct for draft, scheduled, publishing, published, uncertain and failed.

## Responsive Design

- Usable at 390px mobile width.
- Usable at 768px tablet width.
- Usable at desktop width.
- Text does not overflow buttons, cards or preview panels.
- Primary actions remain visible and reachable.

## Product Quality

- No lorem ipsum.
- No fake analytics beyond simple operational counters.
- No landing-page content.
- No Stripe, team admin or extra integrations.
- Demo data is isolated from real API adapters.
- Tokens, secrets and signed URLs are never shown.
