import "server-only";

import { z } from "zod";

const postSchema = z.object({
  id: z.string().uuid(),
  organization_id: z.string().min(1),
  author_id: z.string().min(1),
  content: z.string(),
  status: z.enum([
    "draft",
    "scheduled",
    "publishing",
    "published",
    "partially_failed",
    "failed",
  ]),
  scheduled_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const postListSchema = z.object({
  items: z.array(postSchema),
  limit: z.number(),
  offset: z.number(),
});

export type SocialPost = z.infer<typeof postSchema>;

const workspaceSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  owner_id: z.string(),
  external_organization_id: z.string().nullable(),
  created_at: z.string(),
});

const publicationSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  content_item_id: z.string().uuid(),
  platform_connection_id: z.string().uuid(),
  social_account_id: z.string().uuid(),
  platform: z.string().min(1),
  caption: z.string(),
  media_asset_id: z.string().uuid().nullable(),
  status: z.enum([
    "draft",
    "ready",
    "scheduled",
    "queued",
    "publishing",
    "published",
    "failed_retryable",
    "failed_permanent",
    "uncertain",
    "cancelled",
  ]),
  scheduled_at: z.string().nullable(),
  external_publication_id: z.string().nullable(),
  external_url: z.string().nullable(),
  last_error: z.string().nullable(),
  next_attempt_at: z.string().nullable(),
});

const publicationListSchema = z.object({
  items: z.array(publicationSchema),
});

const publicationAttemptSchema = z.object({
  id: z.string().uuid(),
  publication_id: z.string().uuid(),
  attempt_number: z.number().int().positive(),
  status: z.enum([
    "started",
    "succeeded",
    "failed_retryable",
    "failed_permanent",
  ]),
  provider: z.string(),
  request_id: z.string().nullable(),
  error_code: z.string().nullable(),
  error_message: z.string().nullable(),
  external_publication_id: z.string().nullable(),
  created_at: z.string(),
});

const publicationDetailSchema = publicationSchema.extend({
  attempts: z.array(publicationAttemptSchema),
});

const brandProfileSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  name: z.string(),
  voice: z.string(),
  audience: z.string(),
});

const brandProfileListSchema = z.object({
  items: z.array(brandProfileSchema),
});

const campaignSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  brand_profile_id: z.string().uuid(),
  name: z.string(),
});

const campaignListSchema = z.object({
  items: z.array(campaignSchema),
});

const contentItemSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  campaign_id: z.string().uuid(),
  body: z.string(),
});

const contentItemListSchema = z.object({
  items: z.array(contentItemSchema),
});

const aiGenerationSchema = z.object({
  id: z.string().uuid(),
  operation: z.string(),
  provider: z.string(),
  model: z.string(),
  prompt_version: z.string(),
  input_hash: z.string(),
  token_usage: z.record(z.string(), z.number().int()),
  estimated_cost: z.string(),
  latency_ms: z.number().int(),
  result: z.string(),
  created_at: z.string(),
});

const connectionSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  provider: z.string(),
  platform: z.string().min(1),
  external_account_id: z.string(),
  external_account_name: z.string(),
  capabilities: z.record(z.string(), z.unknown()),
  is_valid: z.boolean(),
  expires_at: z.string().nullable(),
});

const connectionListSchema = z.object({
  items: z.array(connectionSchema),
});

const socialAccountSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  platform_connection_id: z.string().uuid(),
  platform: z.string().min(1),
  account_type: z.string(),
  external_account_id: z.string(),
  display_name: z.string(),
  username: z.string().nullable(),
  capabilities: z.record(z.string(), z.unknown()),
  selected: z.boolean(),
  active: z.boolean(),
  last_validated_at: z.string().nullable(),
});

const socialAccountListSchema = z.object({
  items: z.array(socialAccountSchema),
});

const localDevelopmentSocialAccountsSchema = z.object({
  connections: z.array(connectionSchema),
  accounts: z.array(socialAccountSchema),
});

const mediaUploadTargetSchema = z.object({
  object_key: z.string().min(1),
  upload_url: z.string().url(),
  public_url: z.string().url(),
  method: z.literal("PUT"),
  headers: z.record(z.string(), z.string()),
  expires_at: z.string(),
  max_size_bytes: z.number().int().positive(),
});

const mediaAssetSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  media_type: z.enum(["image", "video"]),
  storage_url: z.string().url(),
  content_type: z.string(),
  checksum_sha256: z.string(),
  storage_key: z.string(),
  size_bytes: z.number().int().nonnegative(),
});

const mediaAssetListSchema = z.object({
  items: z.array(mediaAssetSchema),
});

export type Workspace = z.infer<typeof workspaceSchema>;
export type Publication = z.infer<typeof publicationSchema>;
export type PublicationAttempt = z.infer<typeof publicationAttemptSchema>;
export type PublicationDetail = z.infer<typeof publicationDetailSchema>;
export type BrandProfile = z.infer<typeof brandProfileSchema>;
export type Campaign = z.infer<typeof campaignSchema>;
export type ContentItem = z.infer<typeof contentItemSchema>;
export type AIGeneration = z.infer<typeof aiGenerationSchema>;
export type PlatformConnection = z.infer<typeof connectionSchema>;
export type SocialAccount = z.infer<typeof socialAccountSchema>;
export type MediaUploadTarget = z.infer<typeof mediaUploadTargetSchema>;
export type MediaAsset = z.infer<typeof mediaAssetSchema>;

const providerCapabilitiesSchema = z.object({
  supports_text: z.boolean(),
  supports_single_image: z.boolean(),
  supports_multiple_images: z.boolean(),
  supports_video: z.boolean(),
  supports_reels: z.boolean(),
  supports_stories: z.boolean(),
  supports_scheduling: z.boolean(),
  supports_delete: z.boolean(),
  supports_short_video: z.boolean(),
  supports_comments: z.boolean(),
  supports_analytics: z.boolean(),
  supports_mentions: z.boolean(),
  supports_hashtags: z.boolean(),
  supports_first_comment: z.boolean(),
  requires_public_media_url: z.boolean(),
  max_text_length: z.number().int().nonnegative(),
  supported_media_types: z.array(z.string()),
  daily_publication_limit: z.number().int().nullable(),
});
const providerCatalogSchema = z.object({
  items: z.array(z.object({
    provider: z.string(),
    display_name: z.string(),
    status: z.string(),
    enabled: z.boolean(),
    platforms: z.array(z.object({
      platform: z.string(),
      display_name: z.string(),
      description: z.string(),
      status: z.string(),
      implemented: z.boolean(),
      connected: z.boolean(),
      api_capabilities: providerCapabilitiesSchema,
      capabilities: providerCapabilitiesSchema,
    })),
  })),
});
export type ProviderCatalog = z.infer<typeof providerCatalogSchema>;
export type ProviderPlatform = ProviderCatalog["items"][number]["platforms"][number];

const metaStatusSchema = z.object({
  connections: z.array(z.object({
    id: z.string().uuid(), page_name: z.string(), masked_page_id: z.string(),
    state: z.string(), last_validated_at: z.string().nullable(),
  })),
  accounts: z.array(z.object({
    id: z.string().uuid(), connection_id: z.string().uuid(),
    platform: z.enum(["facebook", "instagram"]), display_name: z.string(),
    username: z.string().nullable(), masked_external_id: z.string(), active: z.boolean(),
    avatar_url: z.string().nullable().optional(), account_type: z.string().nullable().optional(),
    parent_page_name: z.string().nullable().optional(),
  })),
});

export type MetaIntegrationStatus = z.infer<typeof metaStatusSchema>;
export class MetaIntegrationStatusError extends Error {
  constructor(public readonly kind: "not_found" | "access" | "unavailable", message: string) {
    super(message);
    this.name = "MetaIntegrationStatusError";
  }
}
export type MetaConnectionIntent = "facebook" | "instagram" | "combined" | "reconnect";
const metaSessionSchema = z.object({
  session_id: z.string(), connection_intent: z.string(), channel_nonce: z.string(),
  return_to: z.literal("/integrations"), expires_at: z.string(), completed: z.boolean(),
  target_connection_id: z.string().uuid().nullable(),
  candidates: z.array(z.object({
    candidate_id: z.string(), page_name: z.string(), masked_page_id: z.string(),
    page_avatar_url: z.string().nullable().optional(), instagram_username: z.string().nullable(),
    instagram_display_name: z.string().nullable(), instagram_account_type: z.string().nullable(),
    instagram_avatar_url: z.string().nullable().optional(), masked_instagram_id: z.string().nullable(),
    linked_page_name: z.string(), compatible: z.boolean(), compatibility_message: z.string(),
  })), result: z.record(z.string(), z.unknown()).nullable(),
});
export type MetaOAuthSession = z.infer<typeof metaSessionSchema>;

const API_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

// Explicit fallback identity used only when Clerk is disabled for local development.
const developmentIdentity = {
  "X-User-Id": "user_local_founder",
  "X-Organization-Id": "org_local_socialos",
  "X-Organization-Role": "org:admin",
};

async function apiError(response: Response, fallback: string): Promise<string> {
  const payload: unknown = await response.json().catch(() => null);
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export async function getMetaIntegrationStatus(workspaceId: string): Promise<MetaIntegrationStatus> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/integrations/meta`, {
    headers, cache: "no-store",
  });
  if (response.status === 404) throw new MetaIntegrationStatusError("not_found", "Workspace was not found.");
  if (response.status === 401 || response.status === 403) throw new MetaIntegrationStatusError("access", "You do not have access to these connected accounts.");
  if (!response.ok) throw new MetaIntegrationStatusError("unavailable", "Connected account status could not be loaded.");
  try {
    return metaStatusSchema.parse(await response.json());
  } catch {
    throw new MetaIntegrationStatusError("unavailable", "Connected account status returned an invalid response.");
  }
}

export async function authorizeMeta(
  workspaceId: string,
  connectionIntent: MetaConnectionIntent,
  connectionId?: string,
): Promise<{ url: string; channel_nonce: string; return_to: string }> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/integrations/meta/authorize`, {
    method: "POST", headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ connection_intent: connectionIntent, connection_id: connectionId, return_to: "/integrations" }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await apiError(response, "Could not start Meta authorization."));
  return z.object({ url: z.string().url(), channel_nonce: z.string(), return_to: z.literal("/integrations") }).parse(await response.json());
}

export async function disconnectMeta(connectionId: string): Promise<void> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/platform-connections/${connectionId}/disconnect`, { method: "POST", headers, cache: "no-store" });
  if (!response.ok) throw new Error(await apiError(response, "Could not disconnect the Meta account."));
}

export async function validateMeta(connectionId: string): Promise<boolean> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/platform-connections/${connectionId}/validate`, { method: "POST", headers, cache: "no-store" });
  if (!response.ok) throw new Error(await apiError(response, "Could not validate the Meta account."));
  return z.object({ valid: z.boolean() }).parse(await response.json()).valid;
}

export async function getMetaOAuthSession(sessionId: string): Promise<MetaOAuthSession> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/integrations/meta/sessions/${sessionId}`, { headers, cache: "no-store" });
  if (!response.ok) throw new Error(await apiError(response, "Meta selection session is unavailable."));
  return metaSessionSchema.parse(await response.json());
}

export async function selectMetaCandidate(sessionId: string, candidateId: string): Promise<Record<string, unknown>> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/integrations/meta/sessions/${sessionId}/select`, {
    method: "POST", headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId }), cache: "no-store",
  });
  if (!response.ok) throw new Error(await apiError(response, "Could not connect the selected Page."));
  return z.record(z.string(), z.unknown()).parse(await response.json());
}

export async function listPosts(): Promise<SocialPost[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/posts`, {
      headers,
      cache: "no-store",
    });
    if (!response.ok) return [];
    return postListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function ensureWorkspace(
  name = "Kinetic Mobiles",
): Promise<Workspace | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/workspaces`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    return workspaceSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function createBrandProfile(
  workspaceId: string,
  input: {
    name: string;
    voice?: string;
    audience?: string;
  },
): Promise<BrandProfile | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/brand-profiles`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          voice: input.voice ?? "",
          audience: input.audience ?? "",
        }),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return brandProfileSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function createCampaign(
  workspaceId: string,
  input: {
    brand_profile_id: string;
    name: string;
  },
): Promise<Campaign | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/campaigns`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return campaignSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function createContentItem(
  workspaceId: string,
  input: {
    campaign_id: string;
    body: string;
  },
): Promise<ContentItem | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/content-items`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return contentItemSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function adaptContentForPlatform(
  workspaceId: string,
  input: {
    text: string;
    platform: string;
  },
): Promise<AIGeneration | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/ai/adapt-for-platform`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return aiGenerationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function createPublication(
  workspaceId: string,
  input: {
    content_item_id: string;
    platform_connection_id: string;
    social_account_id: string;
    platform: string;
    caption: string;
    media_asset_id?: string | null;
    idempotency_key?: string;
  },
): Promise<Publication | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/publications`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({
          ...input,
          media_asset_id: input.media_asset_id ?? null,
        }),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return publicationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function schedulePublication(
  publicationId: string,
  runAt: string,
): Promise<Publication | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/publications/${publicationId}/schedule`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ run_at: runAt }),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return publicationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function publishPublicationNow(
  publicationId: string,
): Promise<Publication | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/publications/${publicationId}/publish-now`,
      {
        method: "POST",
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return publicationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function listPublications(
  workspaceId: string,
): Promise<Publication[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/publications`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return publicationListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function getPublication(
  publicationId: string,
): Promise<PublicationDetail | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/publications/${publicationId}`, {
      headers,
      cache: "no-store",
    });
    if (!response.ok) return null;
    return publicationDetailSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function retryPublication(
  publicationId: string,
): Promise<Publication | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/publications/${publicationId}/retry`,
      {
        method: "POST",
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return publicationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function cancelPublication(
  publicationId: string,
): Promise<Publication | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/publications/${publicationId}/cancel`,
      {
        method: "POST",
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return publicationSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function listBrandProfiles(
  workspaceId: string,
): Promise<BrandProfile[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/brand-profiles`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return brandProfileListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function listCampaigns(workspaceId: string): Promise<Campaign[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/campaigns`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return campaignListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function listContentItems(
  workspaceId: string,
): Promise<ContentItem[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/content-items`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return contentItemListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function listPlatformConnections(
  workspaceId: string,
): Promise<PlatformConnection[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/platform-connections`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return connectionListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function ensureLocalDevelopmentSocialAccounts(
  workspaceId: string,
): Promise<{
  connections: PlatformConnection[];
  accounts: SocialAccount[];
} | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/platform-connections/local-development`,
      {
        method: "POST",
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return localDevelopmentSocialAccountsSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function listSocialAccounts(
  workspaceId: string,
): Promise<SocialAccount[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/social-accounts`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return socialAccountListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function getProviderCatalog(workspaceId: string): Promise<ProviderCatalog> {
  const headers = await authenticationHeaders();
  const response = await fetch(`${API_URL}/workspaces/${workspaceId}/social/providers`, {
    headers,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await apiError(response, "Provider catalog could not be loaded."));
  return providerCatalogSchema.parse(await response.json());
}

export async function listMediaAssets(
  workspaceId: string,
): Promise<MediaAsset[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/media-assets`,
      {
        headers,
        cache: "no-store",
      },
    );
    if (!response.ok) return [];
    return mediaAssetListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function requestMediaUploadTarget(
  workspaceId: string,
  input: {
    media_type: "image" | "video";
    content_type: string;
    checksum_sha256: string;
    size_bytes: number;
  },
): Promise<MediaUploadTarget | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/media-assets/upload-target`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return mediaUploadTargetSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function registerMediaAsset(
  workspaceId: string,
  input: {
    media_type: "image" | "video";
    storage_url: string;
    content_type: string;
    checksum_sha256: string;
  },
): Promise<MediaAsset | null> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/media-assets`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(input),
        cache: "no-store",
      },
    );
    if (!response.ok) return null;
    return mediaAssetSchema.parse(await response.json());
  } catch {
    return null;
  }
}

export async function uploadMediaAsset(
  workspaceId: string,
  file: File,
): Promise<MediaAsset | null> {
  try {
    const headers = await authenticationHeaders();
    const body = new FormData();
    body.set("file", file, file.name);
    const response = await fetch(
      `${API_URL}/workspaces/${workspaceId}/media-assets/upload`,
      { method: "POST", headers, body, cache: "no-store" },
    );
    if (!response.ok) return null;
    return mediaAssetSchema.parse(await response.json());
  } catch {
    return null;
  }
}

async function authenticationHeaders(): Promise<Record<string, string>> {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return developmentIdentity;
  }

  const { auth } = await import("@clerk/nextjs/server");
  const { getToken, orgId } = await auth();
  if (!orgId) throw new Error("An active organization is required");
  const token = await getToken();
  if (!token) throw new Error("An authenticated session is required");
  return { Authorization: `Bearer ${token}` };
}
