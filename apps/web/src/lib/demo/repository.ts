import type { DemoComposerDraft, DemoPlatform, DemoPublication, DemoState } from "./types";

const STORAGE_KEY = "socialos-demo-state-v1";

export const initialDraft: DemoComposerDraft = {
  originalText:
    "Kinetic Mobiles is launching same-day phone repair for busy local teams. Book online, get transparent pricing, and keep your business moving.",
  selectedPlatforms: ["facebook", "instagram"],
  imageName: "kinetic-mobiles-repair-bench.jpg",
  facebookCaption:
    "Same-day phone repair is now available for local teams. Kinetic Mobiles helps your staff stay connected with fast booking, transparent pricing, and reliable repairs.",
  instagramCaption:
    "Same-day phone repair for busy teams. Fast booking, clear pricing, and devices back in motion. #KineticMobiles #PhoneRepair #LocalBusiness",
};

export function loadDemoState(): DemoState {
  if (typeof window === "undefined") return seedDemoState();
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return seedDemoState();
  try {
    return JSON.parse(stored) as DemoState;
  } catch {
    return seedDemoState();
  }
}

export function saveDemoState(state: DemoState): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function resetDemoState(): DemoState {
  const state = seedDemoState();
  saveDemoState(state);
  return state;
}

export function createDemoPublications(
  state: DemoState,
  draft: DemoComposerDraft,
  status: "published" | "scheduled",
): DemoState {
  const now = new Date().toISOString();
  const created = draft.selectedPlatforms.map((platform) => {
    const account = state.accounts.find((item) => item.platform === platform && item.selected);
    const caption = platform === "facebook" ? draft.facebookCaption : draft.instagramCaption;
    return {
      id: crypto.randomUUID(),
      platform,
      accountId: account?.id ?? `${platform}_missing`,
      caption,
      imageName: draft.imageName,
      scheduledAt: status === "scheduled" ? tomorrowMorningIso() : undefined,
      status,
      externalUrl:
        status === "published"
          ? `https://example.com/kinetic-mobiles/${platform}/${Date.now()}`
          : undefined,
      createdAt: now,
    } satisfies DemoPublication;
  });
  return { ...state, publications: [...created, ...state.publications] };
}

export function retryDemoPublication(state: DemoState, publicationId: string): DemoState {
  return {
    ...state,
    publications: state.publications.map((publication) =>
      publication.id === publicationId
        ? {
            ...publication,
            status: "publishing",
            error: undefined,
          }
        : publication,
    ),
  };
}

export function settleRetry(state: DemoState, publicationId: string): DemoState {
  return {
    ...state,
    publications: state.publications.map((publication) =>
      publication.id === publicationId
        ? {
            ...publication,
            status: "published",
            externalUrl: `https://example.com/kinetic-mobiles/${publication.platform}/${Date.now()}`,
          }
        : publication,
    ),
  };
}

export function adaptCaption(text: string, platform: DemoPlatform): string {
  const trimmed = text.trim();
  if (platform === "instagram") {
    return `${trimmed}\n\nFast, local, and easy to book. #KineticMobiles #PhoneRepair #SmallBusiness`;
  }
  return `${trimmed}\n\nBook your repair online today and keep every workday moving.`;
}

function seedDemoState(): DemoState {
  return {
    accounts: [
      {
        id: "fb_kinetic_page",
        platform: "facebook",
        accountType: "facebook_page",
        displayName: "Kinetic Mobiles",
        selected: true,
        active: true,
        capabilities: {
          supportsText: true,
          supportsSingleImage: true,
          maxTextLength: 63206,
        },
      },
      {
        id: "ig_kinetic_business",
        platform: "instagram",
        accountType: "instagram_business",
        displayName: "Kinetic Mobiles",
        username: "@kineticmobiles",
        selected: true,
        active: true,
        capabilities: {
          supportsText: false,
          supportsSingleImage: true,
          maxTextLength: 2200,
        },
      },
    ],
    publications: [
      {
        id: "pub_demo_published",
        platform: "facebook",
        accountId: "fb_kinetic_page",
        caption:
          "Same-day phone repair for local teams is live. Kinetic Mobiles keeps your staff connected with fast booking and transparent pricing.",
        imageName: "kinetic-mobiles-repair-bench.jpg",
        status: "published",
        externalUrl: "https://example.com/kinetic-mobiles/facebook/demo",
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      },
      {
        id: "pub_demo_uncertain",
        platform: "instagram",
        accountId: "ig_kinetic_business",
        caption:
          "Fast phone repair for busy teams. Book online and get devices back in motion.",
        imageName: "kinetic-mobiles-counter.jpg",
        status: "uncertain",
        error:
          "Meta timed out after accepting the request. SocialOS will reconcile before retrying.",
        createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      },
      {
        id: "pub_demo_failed",
        platform: "instagram",
        accountId: "ig_kinetic_business",
        caption: "A quick launch update without an image.",
        status: "failed",
        error: "Instagram requires an image or video for feed publishing.",
        createdAt: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
      },
    ],
  };
}

function tomorrowMorningIso(): string {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(9, 30, 0, 0);
  return date.toISOString();
}
