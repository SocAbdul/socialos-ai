"use client";

import { Facebook, Instagram, Loader2, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  createMetaCompletionGuard,
  isTrustedMetaPopupMessage,
  META_OAUTH_BROADCAST_CHANNEL,
  META_OAUTH_POPUP_NAME,
  shouldOfferPopupContinuation,
  validateMetaAuthorizationUrl,
} from "@/lib/meta-oauth-client";
import type { MetaConnectionIntent, MetaIntegrationStatus } from "@/lib/api";
import {
  disconnectMetaAction,
  startMetaAuthorization,
  validateMetaAction,
} from "./actions";

type PendingAuthorization = {
  intent: MetaConnectionIntent;
  connectionId?: string;
};

export function IntegrationCards({
  workspaceId,
  status,
}: {
  workspaceId: string;
  status: MetaIntegrationStatus;
}) {
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [continuation, setContinuation] = useState<PendingAuthorization | null>(null);
  const [disconnectTarget, setDisconnectTarget] = useState<string | null>(null);
  const channelNonceRef = useRef<string | null>(null);
  const popupRef = useRef<Window | null>(null);
  const closeWatcherRef = useRef<number | null>(null);
  const completionGuardRef = useRef<((data: unknown) => boolean) | null>(null);

  const clearPopupState = useCallback(() => {
    if (closeWatcherRef.current !== null) window.clearInterval(closeWatcherRef.current);
    closeWatcherRef.current = null;
    popupRef.current = null;
    channelNonceRef.current = null;
    setPending(null);
  }, []);

  const completeAuthorization = useCallback(() => {
    popupRef.current?.close();
    clearPopupState();
    completionGuardRef.current = null;
    setContinuation(null);
    window.location.assign("/integrations");
  }, [clearPopupState]);

  useEffect(() => {
    function receive(event: MessageEvent) {
      if (!isTrustedMetaPopupMessage(event, window.location.origin, popupRef.current, channelNonceRef.current)) return;
      completionGuardRef.current?.(event.data);
    }
    const channel = typeof BroadcastChannel === "undefined"
      ? null
      : new BroadcastChannel(META_OAUTH_BROADCAST_CHANNEL);
    if (channel) channel.onmessage = (event) => completionGuardRef.current?.(event.data);
    window.addEventListener("message", receive);
    return () => {
      window.removeEventListener("message", receive);
      if (closeWatcherRef.current !== null) window.clearInterval(closeWatcherRef.current);
      channel?.close();
    };
  }, [completeAuthorization]);

  async function requestAuthorization(
    request: PendingAuthorization,
    mode: "popup" | "redirect",
  ) {
    setPending(`authorize-${request.connectionId ?? request.intent}`);
    setMessage(null);
    try {
      const result = await startMetaAuthorization(
        workspaceId,
        request.intent,
        request.connectionId,
      );
      const safeUrl = validateMetaAuthorizationUrl(result.url);
      channelNonceRef.current = result.channel_nonce;
      completionGuardRef.current = createMetaCompletionGuard(
        result.channel_nonce,
        completeAuthorization,
      );
      if (mode === "redirect") {
        window.location.assign(safeUrl);
        return;
      }
      const popup = popupRef.current;
      if (!popup || popup.closed) {
        clearPopupState();
        setContinuation(request);
        return;
      }
      popup.location.href = safeUrl;
      closeWatcherRef.current = window.setInterval(() => {
        if (!popup.closed) return;
        const shouldContinue = shouldOfferPopupContinuation(
          popup.closed,
          channelNonceRef.current,
        );
        clearPopupState();
        if (shouldContinue) {
          setContinuation(request);
          setMessage("The Meta window closed before SocialOS received confirmation.");
        }
      }, 500);
    } catch (error) {
      popupRef.current?.close();
      clearPopupState();
      setMessage(error instanceof Error ? error.message : "Could not start Meta authorization.");
    }
  }

  function connect(request: PendingAuthorization) {
    if (pending) return;
    setContinuation(null);
    if (!window.matchMedia("(min-width: 768px)").matches) {
      void requestAuthorization(request, "redirect");
      return;
    }
    const popup = window.open(
      "about:blank",
      META_OAUTH_POPUP_NAME,
      "popup,width=620,height=760",
    );
    popupRef.current = popup;
    if (!popup) {
      setContinuation(request);
      setMessage("Your browser blocked the Meta window.");
      return;
    }
    void requestAuthorization(request, "popup");
  }

  async function mutate(connectionId: string, action: "validate" | "disconnect") {
    if (pending) return;
    setPending(`${action}-${connectionId}`);
    setMessage(null);
    try {
      if (action === "validate") {
        const valid = await validateMetaAction(connectionId);
        setMessage(valid ? "Connection validated." : "Reconnect Meta to restore publishing.");
      } else {
        await disconnectMetaAction(connectionId);
        setMessage("Disconnected from SocialOS. Meta authorization was not revoked.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The action could not be completed.");
    } finally {
      setPending(null);
      setDisconnectTarget(null);
    }
  }

  const facebookConnected = status.accounts.some((item) => item.platform === "facebook" && item.active);
  const instagramConnected = status.accounts.some((item) => item.platform === "instagram" && item.active);

  return <>
    <p className="mb-5 rounded-xl border border-violet-100 bg-violet-50 p-4 text-sm text-violet-900">
      Meta solicitará los permisos necesarios para conectar Facebook e Instagram. Después podrás elegir qué cuentas utilizar en SocialOS.
    </p>
    <div className="grid gap-5 md:grid-cols-2">
      <ChannelCard icon={<Facebook className="size-6" />} title="Facebook" description="Conecta tus páginas de Facebook para publicar y programar contenido." connected={facebookConnected} loading={pending === "authorize-facebook"} onConnect={() => connect({ intent: "facebook" })} />
      <ChannelCard icon={<Instagram className="size-6" />} title="Instagram" description="Conecta una cuenta Business o Creator. Iniciarás sesión con Meta para autorizar la cuenta vinculada." connected={instagramConnected} loading={pending === "authorize-instagram"} onConnect={() => connect({ intent: "instagram" })} />
    </div>
    {continuation ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-sm text-amber-900">Continue securely with a new Meta authorization.</p><Button className="mt-3" disabled={Boolean(pending)} onClick={() => { const request = continuation; setContinuation(null); void requestAuthorization(request, "redirect"); }}>Continuar en esta ventana</Button></div> : null}
    <div className="mt-6 space-y-4" id="connection-list">
      {status.connections.map((connection) => {
        const accounts = status.accounts.filter((item) => item.connection_id === connection.id);
        return <section className="rounded-2xl border border-zinc-200 bg-white p-5" id={`connection-${connection.id}`} key={connection.id}>
          <div className="flex flex-wrap items-center justify-between gap-4"><div><p className="font-semibold text-zinc-950">{connection.page_name}</p><p className="text-sm text-zinc-500">Page ID {connection.masked_page_id} · {connection.state.replaceAll("_", " ")}</p></div><div className="flex flex-wrap gap-2"><Button disabled={Boolean(pending)} type="button" onClick={() => connect({ intent: "reconnect", connectionId: connection.id })}>{pending === `authorize-${connection.id}` ? "Opening Meta..." : "Reconnect"}</Button><Button variant="outline" disabled={Boolean(pending)} type="button" onClick={() => mutate(connection.id, "validate")}>{pending === `validate-${connection.id}` ? "Validating..." : "Validate"}</Button><Button variant="outline" disabled={Boolean(pending)} type="button" onClick={() => setDisconnectTarget(connection.id)}>Disconnect from SocialOS</Button></div></div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">{accounts.map((account) => <div className="rounded-xl bg-zinc-50 p-3" key={account.id}><p className="text-sm font-semibold capitalize">{account.platform}: {account.display_name}</p><p className="text-xs text-zinc-500">{account.masked_external_id} · {account.active ? "Ready" : "Inactive"}</p></div>)}</div>
        </section>;
      })}
    </div>
    {message ? <p aria-live="polite" className="mt-4 rounded-xl bg-violet-50 p-3 text-sm text-violet-800">{message}</p> : null}
    <p className="mt-6 flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck className="size-4" /> SocialOS stores encrypted credentials. Tokens are never shown in the browser.</p>
    {disconnectTarget ? <div aria-labelledby="disconnect-title" aria-modal="true" className="fixed inset-0 z-50 grid place-items-center bg-zinc-950/40 p-4" role="dialog"><div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"><h2 className="text-xl font-bold" id="disconnect-title">Desconectar de SocialOS</h2><p className="mt-3 text-sm leading-6 text-zinc-600">Las publicaciones anteriores permanecerán en tu historial, pero SocialOS dejará de publicar en esta cuenta.</p><div className="mt-6 flex justify-end gap-3"><Button variant="outline" type="button" onClick={() => setDisconnectTarget(null)}>Cancelar</Button><Button disabled={Boolean(pending)} type="button" onClick={() => mutate(disconnectTarget, "disconnect")}>{pending === `disconnect-${disconnectTarget}` ? "Disconnecting..." : "Desconectar de SocialOS"}</Button></div></div></div> : null}
  </>;
}

function ChannelCard({ icon, title, description, connected, loading, onConnect }: { icon: React.ReactNode; title: string; description: string; connected: boolean; loading: boolean; onConnect: () => void }) {
  return <article className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"><div className="flex size-11 items-center justify-center rounded-xl bg-zinc-950 text-white">{icon}</div><h2 className="mt-5 text-xl font-bold">{title}</h2><p className="mt-2 min-h-12 text-sm leading-6 text-zinc-600">{description}</p><div className="mt-5 flex items-center justify-between gap-3"><span className={`text-xs font-semibold ${connected ? "text-emerald-700" : "text-zinc-500"}`}>{connected ? "Connected" : "Not connected"}</span>{connected ? <a className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-semibold" href="#connection-list">Administrar</a> : <Button disabled={loading} onClick={onConnect}>{loading ? <><Loader2 className="animate-spin" /> Opening Meta...</> : `Connect ${title}`}</Button>}</div></article>;
}
