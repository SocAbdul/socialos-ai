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
  getProviderCatalog,
  listPlatformConnections,
  listSocialAccounts,
  publishPublicationNow,
  retryPublication,
  schedulePublication,
  uploadMediaAsset,
} from "@/lib/api";
import { accountsForProvider } from "@/lib/social-account-selection";
import { implementedConnectedImagePlatforms } from "@/lib/provider-catalog";
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
    contentBody,
    delivery,
    captions,
    mediaFile,
    submissionId,
    simulateRetryableError,
    selectedPlatforms,
    voice,
    workspaceId,
  } = validation.data;

  let accounts = await listSocialAccounts(workspaceId);
  const provider = process.env.SOCIAL_PROVIDER === "meta" ? "meta" : "local-dev";
  if (provider === "local-dev" && accounts.length === 0) {
    await ensureLocalDevelopmentSocialAccounts(workspaceId);
    accounts = await listSocialAccounts(workspaceId);
  }
  const connections = await listPlatformConnections(workspaceId);
  const availableAccounts = accountsForProvider(accounts, connections, provider);
  const eligiblePlatforms = provider === "meta"
    ? new Set(
        implementedConnectedImagePlatforms(await getProviderCatalog(workspaceId)).map(
          (item) => item.platform,
        ),
      )
    : new Set(
        availableAccounts
          .filter((account) => account.capabilities.supports_single_image === true)
          .map((account) => account.platform),
      );
  if (selectedPlatforms.some((platform) => !eligiblePlatforms.has(platform))) {
    return actionFailure("One or more selected platforms are not available for image publishing.");
  }

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

  const media = await uploadMediaAsset(workspaceId, mediaFile);
  if (!media) return actionFailure("The image could not be uploaded. Check its format and size.");

  const created = [];
  let aiCost = "0.00";
  for (const platform of selectedPlatforms) {
    const account = availableAccounts.find((item) => item.platform === platform);
    if (!account) return actionFailure(`Connect a compatible ${platform} account first.`);
    const connection = connections.find((item) => item.id === account.platform_connection_id);
    if (!connection) return actionFailure(`The ${platform} connection is unavailable.`);
    const adaptation = await adaptContentForPlatform(workspaceId, { text: content.body, platform });
    if (!adaptation) return actionFailure(`Local ${platform} adaptation failed.`);
    aiCost = adaptation.estimated_cost;
    const editedCaption = captions[platform] ?? "";
    let caption = editedCaption || adaptation.result;
    if (simulateRetryableError && process.env.SOCIAL_PROVIDER !== "meta") {
      caption = `${caption}\n\n[local-retryable-error]`;
    }
    const publication = await createPublication(workspaceId, {
      content_item_id: content.id,
      platform_connection_id: connection.id,
      social_account_id: account.id,
      platform,
      caption,
      media_asset_id: media.id,
      idempotency_key: `${submissionId}:${platform}`,
    });
    if (!publication) return actionFailure(`${platform} publication could not be created.`);
    const queued = delivery === "now"
      ? await publishPublicationNow(publication.id)
      : await schedulePublication(publication.id, new Date(Date.now() + 15 * 60 * 1000).toISOString());
    if (!queued) return actionFailure(`${platform} publication was created but could not be ${delivery === "now" ? "queued" : "scheduled"}.`);
    created.push(queued);
  }

  revalidatePath("/");
  redirect(
    noticeUrl(
      created[0]?.id ?? null,
      `${created.length} platform publication${created.length === 1 ? "" : "s"} ${delivery === "now" ? "queued" : "scheduled"}.`,
      aiCost,
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
