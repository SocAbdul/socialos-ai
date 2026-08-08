import Link from "next/link";

import {
  ensureWorkspace,
  getMetaIntegrationStatus,
  getProviderCatalog,
  MetaIntegrationStatusError,
  type ProviderCatalog,
} from "@/lib/api";
import { IntegrationCards } from "./integration-cards";

export default async function IntegrationsPage({
  searchParams,
}: {
  searchParams?: Promise<{ fixture?: string }>;
}) {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    const params = await searchParams;
    const status = params?.fixture === "connected"
      ? demoConnectedStatus
      : { connections: [], accounts: [] };
    return <IntegrationsShell catalog={demoProviderCatalog} status={status} workspaceId="00000000-0000-4000-8000-000000000001" />;
  }
  const workspace = await ensureWorkspace();
  if (!workspace) return <main className="p-8">Workspace unavailable.</main>;
  let status: Awaited<ReturnType<typeof getMetaIntegrationStatus>>;
  let catalog: ProviderCatalog;
  try {
    [status, catalog] = await Promise.all([
      getMetaIntegrationStatus(workspace.id),
      getProviderCatalog(workspace.id),
    ]);
  } catch (error) {
    const message = error instanceof MetaIntegrationStatusError
      ? error.message
      : "Connected account and provider status could not be loaded.";
    return <main className="min-h-screen bg-[#f8f8fa] p-8"><div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-white p-6"><h1 className="text-2xl font-bold">Cuentas conectadas</h1><p className="mt-3 text-red-700" role="alert">{message}</p><Link className="mt-5 inline-flex font-semibold text-violet-700" href="/">Return to dashboard</Link></div></main>;
  }
  return <IntegrationsShell catalog={catalog} status={status} workspaceId={workspace.id} />;
}

const demoConnectedStatus = {
  connections: [
    { id: "00000000-0000-4000-8000-000000000011", page_name: "Kinetic Mobiles Madrid", masked_page_id: "******1011", state: "connected", last_validated_at: "2026-08-02T12:00:00Z" },
    { id: "00000000-0000-4000-8000-000000000012", page_name: "Kinetic Mobiles Valencia", masked_page_id: "******1012", state: "reauth_required", last_validated_at: null },
  ],
  accounts: [
    { id: "00000000-0000-4000-8000-000000000021", connection_id: "00000000-0000-4000-8000-000000000011", platform: "facebook" as const, display_name: "Kinetic Mobiles Madrid", username: null, masked_external_id: "******2021", active: true },
    { id: "00000000-0000-4000-8000-000000000022", connection_id: "00000000-0000-4000-8000-000000000011", platform: "instagram" as const, display_name: "Kinetic Mobiles", username: "kineticmobiles", masked_external_id: "******2022", active: true },
  ],
};

const emptyCapabilities = {
  supports_text: false, supports_single_image: false, supports_multiple_images: false,
  supports_video: false, supports_reels: false, supports_stories: false,
  supports_scheduling: false, supports_delete: false, supports_short_video: false,
  supports_comments: false, supports_analytics: false, supports_mentions: false,
  supports_hashtags: false, supports_first_comment: false, requires_public_media_url: false,
  max_text_length: 0, supported_media_types: [] as string[], daily_publication_limit: null,
};
const plannedProvider = (provider: string, name: string): ProviderCatalog["items"][number] => ({
  provider,
  display_name: name,
  status: "planned",
  enabled: false,
  platforms: [{
    platform: provider,
    display_name: name,
    description: "Official integration planned",
    status: "planned",
    implemented: false,
    connected: false,
    api_capabilities: emptyCapabilities,
    capabilities: emptyCapabilities,
  }],
});
const demoProviderCatalog: ProviderCatalog = { items: [
  {
    provider: "meta", display_name: "Meta", status: "verified_in_development", enabled: true,
    platforms: [
      { platform: "facebook", display_name: "Facebook", description: "Pages", status: "verified_in_development", implemented: true, connected: true, api_capabilities: { ...emptyCapabilities, supports_text: true, supports_single_image: true }, capabilities: { ...emptyCapabilities, supports_text: true, supports_single_image: true } },
      { platform: "instagram", display_name: "Instagram", description: "Business or Creator accounts", status: "verified_in_development", implemented: true, connected: true, api_capabilities: { ...emptyCapabilities, supports_single_image: true }, capabilities: { ...emptyCapabilities, supports_single_image: true } },
    ],
  },
  plannedProvider("linkedin", "LinkedIn"),
  plannedProvider("youtube", "YouTube"),
  plannedProvider("tiktok", "TikTok"),
  plannedProvider("reddit", "Reddit"),
] };

function IntegrationsShell({
  catalog,
  workspaceId,
  status,
}: {
  catalog: ProviderCatalog;
  workspaceId: string;
  status: Awaited<ReturnType<typeof getMetaIntegrationStatus>>;
}) {
  return <main className="min-h-screen bg-[#f8f8fa] p-5 sm:p-8"><div className="mx-auto max-w-5xl"><Link className="text-sm font-semibold text-violet-700" href="/">← Dashboard</Link><div className="mb-8 mt-5"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-600">SocialOS connections</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Cuentas conectadas</h1><p className="mt-2 text-zinc-600">Conecta tus redes sociales para publicar y programar contenido desde SocialOS.</p></div><IntegrationCards catalog={catalog} status={status} workspaceId={workspaceId} /></div></main>;
}
