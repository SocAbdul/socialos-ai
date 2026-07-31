import { z } from "zod";

export const walkthroughLimits = {
  brandName: 160,
  campaignName: 180,
  profileText: 2_000,
  contentBody: 5_000,
  mediaUrl: 2_048,
} as const;

const requiredText = (label: string, maxLength: number) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required.`)
    .max(
      maxLength,
      `${label} must be ${maxLength.toLocaleString()} characters or fewer.`,
    );

export const walkthroughSchema = z.object({
  workspaceId: z.string().uuid(),
  brandName: requiredText("Brand Profile", walkthroughLimits.brandName),
  campaignName: requiredText("Campaign", walkthroughLimits.campaignName),
  voice: requiredText("Brand voice", walkthroughLimits.profileText),
  audience: requiredText("Audience", walkthroughLimits.profileText),
  contentBody: requiredText("Original content", walkthroughLimits.contentBody),
  platform: z.enum(["facebook", "instagram"], {
    error: "Select Facebook or Instagram.",
  }),
  mediaUrl: requiredText("Media Asset URL", walkthroughLimits.mediaUrl).refine(
    (value) => {
      try {
        return ["http:", "https:"].includes(new URL(value).protocol);
      } catch {
        return false;
      }
    },
    "Enter a complete http or https URL.",
  ),
  contentType: z.string().trim().min(1).max(128),
  checksumSha256: z.string().regex(/^[a-f0-9]{64}$/i),
  simulateRetryableError: z.boolean(),
});

export type WalkthroughField = keyof z.infer<typeof walkthroughSchema>;
export type WalkthroughFieldErrors = Partial<Record<WalkthroughField, string>>;
type WalkthroughValidationResult =
  | { data: z.infer<typeof walkthroughSchema>; errors: WalkthroughFieldErrors }
  | { data: null; errors: WalkthroughFieldErrors };

export function walkthroughInput(formData: FormData) {
  return {
    workspaceId: formData.get("workspaceId"),
    brandName: formData.get("brandName"),
    campaignName: formData.get("campaignName"),
    voice: formData.get("voice"),
    audience: formData.get("audience"),
    contentBody: formData.get("contentBody"),
    platform: formData.get("platform"),
    mediaUrl: formData.get("mediaUrl"),
    contentType: formData.get("contentType"),
    checksumSha256: formData.get("checksumSha256"),
    simulateRetryableError: formData.get("simulateRetryableError") === "on",
  };
}

export function validateWalkthrough(
  formData: FormData,
): WalkthroughValidationResult {
  const result = walkthroughSchema.safeParse(walkthroughInput(formData));
  if (result.success) return { data: result.data, errors: {} };

  const errors: WalkthroughFieldErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as WalkthroughField | undefined;
    if (field && !errors[field]) errors[field] = issue.message;
  }
  return { data: null, errors };
}
