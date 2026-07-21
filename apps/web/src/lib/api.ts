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
  platform: z.enum(["facebook", "instagram"]),
  caption: z.string(),
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

const connectionSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  provider: z.string(),
  platform: z.enum(["facebook", "instagram"]),
  external_account_id: z.string(),
  external_account_name: z.string(),
  capabilities: z.record(z.string(), z.unknown()),
  is_valid: z.boolean(),
  expires_at: z.string().nullable(),
});

const connectionListSchema = z.object({
  items: z.array(connectionSchema),
});

export type Workspace = z.infer<typeof workspaceSchema>;
export type Publication = z.infer<typeof publicationSchema>;
export type PlatformConnection = z.infer<typeof connectionSchema>;

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

export async function ensureWorkspace(name = "Kinetic Mobiles"): Promise<Workspace | null> {
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

export async function listPublications(workspaceId: string): Promise<Publication[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/workspaces/${workspaceId}/publications`, {
      headers,
      cache: "no-store",
    });
    if (!response.ok) return [];
    return publicationListSchema.parse(await response.json()).items;
  } catch {
    return [];
  }
}

export async function listPlatformConnections(workspaceId: string): Promise<PlatformConnection[]> {
  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/workspaces/${workspaceId}/platform-connections`, {
      headers,
      cache: "no-store",
    });
    if (!response.ok) return [];
    return connectionListSchema.parse(await response.json()).items;
  } catch {
    return [];
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
