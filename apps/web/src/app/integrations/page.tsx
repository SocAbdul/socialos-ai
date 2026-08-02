import Link from "next/link";

import { IntegrationCards } from "./integration-cards";
import { ensureWorkspace, getMetaIntegrationStatus, MetaIntegrationStatusError } from "@/lib/api";

export default async function IntegrationsPage({ searchParams }: { searchParams?: Promise<{ fixture?: string }> }) {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    const params = await searchParams;
    const status = params?.fixture === "connected" ? demoConnectedStatus : { connections: [], accounts: [] };
    return <IntegrationsShell workspaceId="00000000-0000-4000-8000-000000000001" status={status} />;
  }
  const workspace = await ensureWorkspace();
  if (!workspace) return <main className="p-8">Workspace unavailable.</main>;
  let status;
  try {
    status = await getMetaIntegrationStatus(workspace.id);
  } catch (error) {
    const message = error instanceof MetaIntegrationStatusError ? error.message : "Connected account status could not be loaded.";
    return <main className="min-h-screen bg-[#f8f8fa] p-8"><div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-white p-6"><h1 className="text-2xl font-bold">Cuentas conectadas</h1><p role="alert" className="mt-3 text-red-700">{message}</p><Link className="mt-5 inline-flex font-semibold text-violet-700" href="/">Return to dashboard</Link></div></main>;
  }
  return <IntegrationsShell workspaceId={workspace.id} status={status} />;
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

function IntegrationsShell({ workspaceId, status }: { workspaceId: string; status: Awaited<ReturnType<typeof getMetaIntegrationStatus>> }) {
  return <main className="min-h-screen bg-[#f8f8fa] p-5 sm:p-8"><div className="mx-auto max-w-5xl"><Link className="text-sm font-semibold text-violet-700" href="/">← Dashboard</Link><div className="mb-8 mt-5"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-600">SocialOS connections</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Cuentas conectadas</h1><p className="mt-2 text-zinc-600">Conecta tus redes sociales para publicar y programar contenido desde SocialOS.</p></div><IntegrationCards workspaceId={workspaceId} status={status} /></div></main>;
}
