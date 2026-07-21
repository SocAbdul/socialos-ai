export type DemoPlatform = "facebook" | "instagram";

export type DemoPublicationStatus =
  | "draft"
  | "scheduled"
  | "publishing"
  | "published"
  | "uncertain"
  | "failed";

export type DemoSocialAccount = {
  id: string;
  platform: DemoPlatform;
  accountType: "facebook_page" | "instagram_business";
  displayName: string;
  username?: string;
  selected: boolean;
  active: boolean;
  capabilities: {
    supportsText: boolean;
    supportsSingleImage: boolean;
    maxTextLength: number;
  };
};

export type DemoPublication = {
  id: string;
  platform: DemoPlatform;
  accountId: string;
  caption: string;
  imageName?: string;
  scheduledAt?: string;
  status: DemoPublicationStatus;
  externalUrl?: string;
  error?: string;
  createdAt: string;
};

export type DemoState = {
  accounts: DemoSocialAccount[];
  publications: DemoPublication[];
};

export type DemoComposerDraft = {
  originalText: string;
  selectedPlatforms: DemoPlatform[];
  imageName: string;
  facebookCaption: string;
  instagramCaption: string;
};
