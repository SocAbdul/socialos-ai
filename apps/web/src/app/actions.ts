"use server";

import { revalidatePath } from "next/cache";
import type { Route } from "next";
import { redirect } from "next/navigation";

import {
  adaptContentForPlatform,
  cancelPublication,
  createBrandProfile,
  createCampaign,
  createContentItem,
  createPublication,
  ensureLocalDevelopmentSocialAccounts,
  listPlatformConnections,
  listSocialAccounts,
  publishPublicationNow,
  registerMediaAsset,
  retryPublication,
  schedulePublication,
} from "@/lib/api";

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function noticeUrl(publicationId: string | null, notice: string): Route {
  const params = new URLSearchParams({ notice });
  if (publicationId) params.set("publication", publicationId);
  return `/?${params.toString()}` as Route;
}

export async function ensureLocalDevelopmentAccountsAction(formData: FormData) {
  const workspaceId = field(formData, "workspaceId");
  const result = await ensureLocalDevelopmentSocialAccounts(workspaceId);
  if (!result) {
    redirect(noticeUrl(null, "Could not create local development accounts."));
  }
  revalidatePath("/");
  redirect(noticeUrl(null, "Local development accounts are ready."));
}

export async function createWalkthroughPublicationAction(formData: FormData) {
  const workspaceId = field(formData, "workspaceId");
  const platform = field(formData, "platform") as "facebook" | "instagram";
  const brandName = field(formData, "brandName");
  const voice = field(formData, "voice");
  const audience = field(formData, "audience");
  const campaignName = field(formData, "campaignName");
  const contentBody = field(formData, "contentBody");
  const contentType = field(formData, "contentType") || "image/jpeg";
  const mediaUrl =
    field(formData, "mediaUrl") ||
    "https://media.local.socialos.invalid/kinetic-mobiles/same-day-screen-repair.jpg";
  const checksum =
    field(formData, "checksumSha256") ||
    "b4b9b02e6f09a9bd760f388b67351e2b1dd3bba6a63c10cf7e5f541d176ad39c";
  const simulateRetryableError = field(formData, "simulateRetryableError") === "on";

  const brand = await createBrandProfile(workspaceId, {
    name: brandName,
    voice,
    audience,
  });
  if (!brand) redirect(noticeUrl(null, "Brand profile could not be created."));

  const campaign = await createCampaign(workspaceId, {
    brand_profile_id: brand.id,
    name: campaignName,
  });
  if (!campaign) redirect(noticeUrl(null, "Campaign could not be created."));

  const content = await createContentItem(workspaceId, {
    campaign_id: campaign.id,
    body: contentBody,
  });
  if (!content) redirect(noticeUrl(null, "Content item could not be created."));

  const adaptation = await adaptContentForPlatform(workspaceId, {
    text: content.body,
    platform,
  });
  if (!adaptation) redirect(noticeUrl(null, "Local AI adaptation failed."));

  const media = await registerMediaAsset(workspaceId, {
    media_type: "image",
    storage_url: mediaUrl,
    content_type: contentType,
    checksum_sha256: checksum,
  });
  if (!media) redirect(noticeUrl(null, "Media asset could not be registered."));

  let accounts = await listSocialAccounts(workspaceId);
  if (!accounts.some((account) => account.platform === platform)) {
    await ensureLocalDevelopmentSocialAccounts(workspaceId);
    accounts = await listSocialAccounts(workspaceId);
  }
  const account = accounts.find((item) => item.platform === platform);
  if (!account) redirect(noticeUrl(null, "No local social account is available."));

  const connections = await listPlatformConnections(workspaceId);
  const connection = connections.find(
    (item) => item.id === account.platform_connection_id,
  );
  if (!connection) redirect(noticeUrl(null, "No local platform connection is available."));

  const caption = simulateRetryableError
    ? `${adaptation.result}\n\n[local-retryable-error]`
    : adaptation.result;
  const publication = await createPublication(workspaceId, {
    content_item_id: content.id,
    platform_connection_id: connection.id,
    social_account_id: account.id,
    platform,
    caption,
    media_asset_id: media.id,
  });
  if (!publication) redirect(noticeUrl(null, "Publication could not be created."));

  revalidatePath("/");
  redirect(noticeUrl(publication.id, "Publication created and ready."));
}

export async function publishNowAction(formData: FormData) {
  const publicationId = field(formData, "publicationId");
  const publication = await publishPublicationNow(publicationId);
  revalidatePath("/");
  redirect(
    noticeUrl(
      publicationId,
      publication ? "Publication queued for local worker." : "Publication could not be queued.",
    ),
  );
}

export async function scheduleAction(formData: FormData) {
  const publicationId = field(formData, "publicationId");
  const runAt = new Date(Date.now() + 15 * 60 * 1000).toISOString();
  const publication = await schedulePublication(publicationId, runAt);
  revalidatePath("/");
  redirect(
    noticeUrl(
      publicationId,
      publication ? "Publication scheduled 15 minutes from now." : "Publication could not be scheduled.",
    ),
  );
}

export async function retryAction(formData: FormData) {
  const publicationId = field(formData, "publicationId");
  const publication = await retryPublication(publicationId);
  revalidatePath("/");
  redirect(
    noticeUrl(
      publicationId,
      publication ? "Retry queued for local worker." : "Publication cannot be retried now.",
    ),
  );
}

export async function cancelAction(formData: FormData) {
  const publicationId = field(formData, "publicationId");
  const publication = await cancelPublication(publicationId);
  revalidatePath("/");
  redirect(
    noticeUrl(
      publicationId,
      publication ? "Publication cancelled." : "Publication cannot be cancelled now.",
    ),
  );
}
