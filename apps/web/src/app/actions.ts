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
import { accountsForProvider } from "@/lib/social-account-selection";
import {
  type WalkthroughFieldErrors,
  validateWalkthrough,
} from "@/lib/walkthrough-validation";

export type WalkthroughActionState = {
  errors: WalkthroughFieldErrors;
  message: string | null;
};

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function noticeUrl(
  publicationId: string | null,
  notice: string,
  aiCost?: string,
): Route {
  const params = new URLSearchParams({ notice });
  if (publicationId) params.set("publication", publicationId);
  if (aiCost) params.set("aiCost", aiCost);
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

export async function createWalkthroughPublicationAction(
  _previousState: WalkthroughActionState,
  formData: FormData,
): Promise<WalkthroughActionState> {
  const validation = validateWalkthrough(formData);
  if (!validation.data) {
    return {
      errors: validation.errors,
      message: "Nothing was saved. Complete the required fields and try again.",
    };
  }
  const {
    audience,
    brandName,
    campaignName,
    checksumSha256: checksum,
    contentBody,
    contentType,
    mediaUrl,
    platform,
    simulateRetryableError,
    voice,
    workspaceId,
  } = validation.data;

  const brand = await createBrandProfile(workspaceId, {
    name: brandName,
    voice,
    audience,
  });
  if (!brand) return actionFailure("Brand profile could not be created.");

  const campaign = await createCampaign(workspaceId, {
    brand_profile_id: brand.id,
    name: campaignName,
  });
  if (!campaign) return actionFailure("Campaign could not be created.");

  const content = await createContentItem(workspaceId, {
    campaign_id: campaign.id,
    body: contentBody,
  });
  if (!content) return actionFailure("Content item could not be created.");

  const adaptation = await adaptContentForPlatform(workspaceId, {
    text: content.body,
    platform,
  });
  if (!adaptation) return actionFailure("Local AI adaptation failed.");

  const media = await registerMediaAsset(workspaceId, {
    media_type: "image",
    storage_url: mediaUrl,
    content_type: contentType,
    checksum_sha256: checksum,
  });
  if (!media) return actionFailure("Check the Media Asset URL and try again.");

  let accounts = await listSocialAccounts(workspaceId);
  if (
    process.env.SOCIAL_PROVIDER !== "meta" &&
    !accounts.some((account) => account.platform === platform)
  ) {
    await ensureLocalDevelopmentSocialAccounts(workspaceId);
    accounts = await listSocialAccounts(workspaceId);
  }
  const connections = await listPlatformConnections(workspaceId);
  const provider = process.env.SOCIAL_PROVIDER === "meta" ? "meta" : "local-dev";
  const account = accountsForProvider(accounts, connections, provider).find(
    (item) => item.platform === platform,
  );
  if (!account)
    return actionFailure(
      process.env.SOCIAL_PROVIDER === "meta"
        ? "Connect a compatible Meta account before creating this publication."
        : "No local social account is available.",
    );

  const connection = connections.find(
    (item) => item.id === account.platform_connection_id,
  );
  if (!connection)
    return actionFailure("No compatible platform connection is available.");

  const caption = simulateRetryableError && process.env.SOCIAL_PROVIDER !== "meta"
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
  if (!publication) return actionFailure("Publication could not be created.");

  revalidatePath("/");
  redirect(
    noticeUrl(
      publication.id,
      "Publication created and ready.",
      adaptation.estimated_cost,
    ),
  );
}

function actionFailure(message: string): WalkthroughActionState {
  return { errors: {}, message };
}

export async function publishNowAction(formData: FormData) {
  const publicationId = field(formData, "publicationId");
  const publication = await publishPublicationNow(publicationId);
  revalidatePath("/");
  redirect(
    noticeUrl(
      publicationId,
      publication
        ? "Publication queued for delivery."
        : "Publication could not be queued.",
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
      publication
        ? "Publication scheduled 15 minutes from now."
        : "Publication could not be scheduled.",
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
      publication
        ? "Retry queued for delivery."
        : "Publication cannot be retried now.",
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
      publication
        ? "Publication cancelled."
        : "Publication cannot be cancelled now.",
    ),
  );
}
