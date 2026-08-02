import Link from "next/link";

import { IntegrationCards } from "./integration-cards";
import { ensureWorkspace, getMetaIntegrationStatus } from "@/lib/api";

export default async function IntegrationsPage() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return <IntegrationsShell workspaceId="00000000-0000-4000-8000-000000000001" status={{ connections: [], accounts: [] }} />;
  }
  const workspace = await ensureWorkspace();
  if (!workspace) return <main className="p-8">Workspace unavailable.</main>;
  const status = await getMetaIntegrationStatus(workspace.id);
  return <IntegrationsShell workspaceId={workspace.id} status={status} />;
}

function IntegrationsShell({ workspaceId, status }: { workspaceId: string; status: Awaited<ReturnType<typeof getMetaIntegrationStatus>> }) {
  return <main className="min-h-screen bg-[#f8f8fa] p-5 sm:p-8"><div className="mx-auto max-w-5xl"><Link className="text-sm font-semibold text-violet-700" href="/">← Dashboard</Link><div className="mb-8 mt-5"><p className="text-xs font-bold uppercase tracking-[.18em] text-violet-600">SocialOS connections</p><h1 className="mt-2 text-3xl font-bold tracking-tight">Cuentas conectadas</h1><p className="mt-2 text-zinc-600">Conecta tus redes sociales para publicar y programar contenido desde SocialOS.</p></div><IntegrationCards workspaceId={workspaceId} status={status} /></div></main>;
}
