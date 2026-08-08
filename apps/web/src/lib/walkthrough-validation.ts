import { z } from "zod";

export const walkthroughLimits = {
  brandName: 160,
  campaignName: 180,
  profileText: 2_000,
  contentBody: 5_000,
  caption: 5_000,
} as const;

const requiredText = (label: string, maxLength: number) =>
  z.string().trim().min(1, `${label} is required.`).max(maxLength);

const text = (maxLength: number) => z.string().trim().max(maxLength);

export const walkthroughSchema = z
  .object({
    workspaceId: z.string().uuid(),
    submissionId: z.string().min(16).max(96),
    delivery: z.enum(["now", "schedule"]),
    brandName: requiredText("Brand Profile", walkthroughLimits.brandName),
    campaignName: requiredText("Campaign", walkthroughLimits.campaignName),
    voice: requiredText("Brand voice", walkthroughLimits.profileText),
    audience: requiredText("Audience", walkthroughLimits.profileText),
    contentBody: requiredText("Original content", walkthroughLimits.contentBody),
    facebook: z.boolean(),
    instagram: z.boolean(),
    facebookCaption: text(walkthroughLimits.caption),
    instagramCaption: text(walkthroughLimits.caption),
    simulateRetryableError: z.boolean(),
  })
  .refine((value) => value.facebook || value.instagram, {
    path: ["platforms"],
    message: "Select at least one connected platform.",
  });

export type WalkthroughField =
  | keyof z.infer<typeof walkthroughSchema>
  | "platforms"
  | "mediaFile";
export type WalkthroughFieldErrors = Partial<Record<WalkthroughField, string>>;
export type WalkthroughData = z.infer<typeof walkthroughSchema> & { mediaFile: File };
type WalkthroughValidationResult =
  | { data: WalkthroughData; errors: WalkthroughFieldErrors }
  | { data: null; errors: WalkthroughFieldErrors };

export function walkthroughInput(formData: FormData) {
  return {
    workspaceId: formData.get("workspaceId"),
    submissionId: formData.get("submissionId"),
    delivery: formData.get("delivery"),
    brandName: formData.get("brandName"),
    campaignName: formData.get("campaignName"),
    voice: formData.get("voice"),
    audience: formData.get("audience"),
    contentBody: formData.get("contentBody"),
    facebook: formData.get("facebook") === "on",
    instagram: formData.get("instagram") === "on",
    facebookCaption: formData.get("facebookCaption") ?? "",
    instagramCaption: formData.get("instagramCaption") ?? "",
    simulateRetryableError: formData.get("simulateRetryableError") === "on",
  };
}

export function validateWalkthrough(formData: FormData): WalkthroughValidationResult {
  const result = walkthroughSchema.safeParse(walkthroughInput(formData));
  const errors: WalkthroughFieldErrors = {};
  if (!result.success) {
    for (const issue of result.error.issues) {
      const field = issue.path[0] as WalkthroughField | undefined;
      if (field && !errors[field]) errors[field] = issue.message;
    }
  }
  const mediaFile = formData.get("mediaFile");
  if (!(mediaFile instanceof File) || mediaFile.size === 0) {
    errors.mediaFile = "Choose a JPEG or PNG image.";
  } else if (!["image/jpeg", "image/png"].includes(mediaFile.type)) {
    errors.mediaFile = "Only JPEG and PNG images are supported.";
  } else if (mediaFile.size > 15 * 1024 * 1024) {
    errors.mediaFile = "Image must be 15 MB or smaller.";
  }
  if (!result.success || Object.keys(errors).length > 0) return { data: null, errors };
  return { data: { ...result.data, mediaFile: mediaFile as File }, errors: {} };
}
