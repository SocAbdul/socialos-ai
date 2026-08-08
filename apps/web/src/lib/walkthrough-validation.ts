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
const platformIdentifier = z.string().trim().min(1).max(80).regex(/^[a-z0-9_-]+$/);

export const walkthroughSchema = z.object({
  workspaceId: z.string().uuid(),
  submissionId: z.string().min(16).max(96),
  delivery: z.enum(["now", "schedule"]),
  brandName: requiredText("Brand Profile", walkthroughLimits.brandName),
  campaignName: requiredText("Campaign", walkthroughLimits.campaignName),
  voice: requiredText("Brand voice", walkthroughLimits.profileText),
  audience: requiredText("Audience", walkthroughLimits.profileText),
  contentBody: requiredText("Original content", walkthroughLimits.contentBody),
  selectedPlatforms: z.array(platformIdentifier).min(1, "Select at least one connected platform."),
  captions: z.record(platformIdentifier, text(walkthroughLimits.caption)),
  simulateRetryableError: z.boolean(),
});

export type WalkthroughField =
  | keyof z.infer<typeof walkthroughSchema>
  | "platforms"
  | "mediaFile"
  | `caption:${string}`;
export type WalkthroughFieldErrors = Partial<Record<WalkthroughField, string>>;
export type WalkthroughData = z.infer<typeof walkthroughSchema> & { mediaFile: File };
type WalkthroughValidationResult =
  | { data: WalkthroughData; errors: WalkthroughFieldErrors }
  | { data: null; errors: WalkthroughFieldErrors };

export function walkthroughInput(formData: FormData) {
  const selectedPlatforms = Array.from(new Set(formData.getAll("platform").filter(
    (value): value is string => typeof value === "string",
  )));
  return {
    workspaceId: formData.get("workspaceId"),
    submissionId: formData.get("submissionId"),
    delivery: formData.get("delivery"),
    brandName: formData.get("brandName"),
    campaignName: formData.get("campaignName"),
    voice: formData.get("voice"),
    audience: formData.get("audience"),
    contentBody: formData.get("contentBody"),
    selectedPlatforms,
    captions: Object.fromEntries(
      selectedPlatforms.map((platform) => [
        platform,
        formData.get(`caption:${platform}`) ?? "",
      ]),
    ),
    simulateRetryableError: formData.get("simulateRetryableError") === "on",
  };
}

export function validateWalkthrough(formData: FormData): WalkthroughValidationResult {
  const result = walkthroughSchema.safeParse(walkthroughInput(formData));
  const errors: WalkthroughFieldErrors = {};
  if (!result.success) {
    for (const issue of result.error.issues) {
      const field = issue.path[0] === "selectedPlatforms"
        ? "platforms"
        : issue.path[0] === "captions" && typeof issue.path[1] === "string"
          ? `caption:${issue.path[1]}` as const
          : issue.path[0] as WalkthroughField | undefined;
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
