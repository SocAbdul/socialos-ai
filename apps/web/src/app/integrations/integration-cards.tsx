"use client";

import { Facebook, Instagram, Loader2, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type { MetaConnectionIntent, MetaIntegrationStatus } from "@/lib/api";
import {
  disconnectMetaAction,
  startMetaAuthorization,
  validateMetaAction,
} from "./actions";

export function IntegrationCards({ workspaceId, status }: { workspaceId: string; status: MetaIntegrationStatus }) {
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const channelNonce = useRef<string | null>(null);
  const connected = status.connections[0];

  useEffect(() => {
    function receive(event: MessageEvent) {
      const data = event.data as { type?: string; channelNonce?: string } | null;
      if (event.origin !== window.location.origin || data?.type !== "socialos:meta-connected" || data.channelNonce !== channelNonce.current) return;
      channelNonce.current = null;
      setPending(null);
      window.location.reload();
    }
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);

  async function connect(intent: MetaConnectionIntent) {
    if (pending) return;
    setPending(intent);
    setMessage(null);
    const usePopup = window.matchMedia("(min-width: 768px)").matches;
    const popup = usePopup ? window.open("about:blank", "socialos-meta", "popup,width=620,height=760") : null;
    try {
      const result = await startMetaAuthorization(
        workspaceId,
        intent,
        intent === "reconnect" ? connected?.id : undefined,
      );
      channelNonce.current = result.channel_nonce;
      if (popup && !popup.closed) {
        popup.location.href = result.url;
        const closeWatcher = window.setInterval(() => {
          if (!popup.closed) return;
          window.clearInterval(closeWatcher);
          if (channelNonce.current === result.channel_nonce) window.location.assign(result.url);
        }, 500);
      } else window.location.assign(result.url);
    } catch (error) {
      popup?.close();
      setMessage(error instanceof Error ? error.message : "Could not start Meta authorization.");
      setPending(null);
    }
  }

  async function mutate(action: "validate" | "disconnect") {
    if (!connected || pending) return;
    setPending(action);
    setMessage(null);
    try {
      if (action === "validate") {
        const valid = await validateMetaAction(connected.id);
        setMessage(valid ? "Connection validated." : "Reconnect Meta to restore publishing.");
      } else {
        await disconnectMetaAction(connected.id);
        setMessage("Disconnected from SocialOS. Meta authorization was not revoked.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The action could not be completed.");
    } finally {
      setPending(null);
    }
  }

  return <>
    <div className="grid gap-5 md:grid-cols-2">
      <ChannelCard icon={<Facebook className="size-6" />} title="Facebook" description="Conecta tus páginas de Facebook para publicar y programar contenido." connected={Boolean(status.accounts.find((a) => a.platform === "facebook" && a.active))} loading={pending === "facebook"} onConnect={() => connect("facebook")} />
      <ChannelCard icon={<Instagram className="size-6" />} title="Instagram" description="Conecta una cuenta Business o Creator. Iniciarás sesión con Meta para autorizar la cuenta vinculada." connected={Boolean(status.accounts.find((a) => a.platform === "instagram" && a.active))} loading={pending === "instagram"} onConnect={() => connect("instagram")} />
    </div>
    {connected ? <section className="mt-6 rounded-2xl border border-zinc-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-4"><div><p className="font-semibold text-zinc-950">{connected.page_name}</p><p className="text-sm text-zinc-500">Page ID {connected.masked_page_id} · {connected.state.replaceAll("_", " ")}</p></div><div className="flex flex-wrap gap-2">{connected.state !== "connected" ? <Button disabled={Boolean(pending)} onClick={() => connect("reconnect")}>{pending === "reconnect" ? "Opening Meta..." : "Reconnect"}</Button> : null}<Button variant="outline" disabled={Boolean(pending)} onClick={() => mutate("validate")}>{pending === "validate" ? "Validating..." : "Validate"}</Button><Button variant="outline" disabled={Boolean(pending)} onClick={() => mutate("disconnect")}>{pending === "disconnect" ? "Disconnecting..." : "Disconnect from SocialOS"}</Button></div></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">{status.accounts.filter((a) => a.connection_id === connected.id).map((account) => <div className="rounded-xl bg-zinc-50 p-3" key={account.id}><p className="text-sm font-semibold capitalize">{account.platform}: {account.display_name}</p><p className="text-xs text-zinc-500">{account.masked_external_id} · {account.active ? "Ready" : "Inactive"}</p></div>)}</div>
    </section> : null}
    {message ? <p aria-live="polite" className="mt-4 rounded-xl bg-violet-50 p-3 text-sm text-violet-800">{message}</p> : null}
    <p className="mt-6 flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck className="size-4" /> SocialOS stores encrypted credentials. Tokens are never shown in the browser.</p>
  </>;
}

function ChannelCard({ icon, title, description, connected, loading, onConnect }: { icon: React.ReactNode; title: string; description: string; connected: boolean; loading: boolean; onConnect: () => void }) {
  return <article className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"><div className="flex size-11 items-center justify-center rounded-xl bg-zinc-950 text-white">{icon}</div><h2 className="mt-5 text-xl font-bold">{title}</h2><p className="mt-2 min-h-12 text-sm leading-6 text-zinc-600">{description}</p><div className="mt-5 flex items-center justify-between gap-3"><span className={`text-xs font-semibold ${connected ? "text-emerald-700" : "text-zinc-500"}`}>{connected ? "Connected" : "Not connected"}</span><Button disabled={loading} onClick={onConnect}>{loading ? <><Loader2 className="animate-spin" /> Opening Meta...</> : `Connect ${title}`}</Button></div></article>;
}
