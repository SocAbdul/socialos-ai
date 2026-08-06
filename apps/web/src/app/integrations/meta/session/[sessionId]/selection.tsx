"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import type { MetaOAuthSession } from "@/lib/api";
import {
  completeMetaSelection,
  META_OAUTH_BROADCAST_CHANNEL,
  META_OAUTH_POPUP_NAME,
  type MetaCompletionMessage,
} from "@/lib/meta-oauth-client";
import { selectMetaCandidateAction } from "../../../actions";

export function MetaSelection({ session }: { session: MetaOAuthSession }) {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  async function select(candidateId: string) {
    if (pending) return;
    setPending(candidateId); setError(null);
    try {
      await selectMetaCandidateAction(session.session_id, candidateId);
      const channel = typeof BroadcastChannel === "undefined"
        ? null
        : new BroadcastChannel(META_OAUTH_BROADCAST_CHANNEL);
      completeMetaSelection({
        channelNonce: session.channel_nonce,
        isPopup: window.name === META_OAUTH_POPUP_NAME,
        hasOpener: Boolean(window.opener && !window.opener.closed),
        postToOpener: (message: MetaCompletionMessage) =>
          window.opener?.postMessage(message, window.location.origin),
        broadcast: (message: MetaCompletionMessage) => channel?.postMessage(message),
        closePopup: () => window.close(),
        navigate: () => router.replace(session.return_to),
      });
      channel?.close();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not connect this Page.");
      setPending(null);
    }
  }
  return <div className="space-y-4">{session.candidates.map((candidate) => <article className="rounded-2xl border border-zinc-200 bg-white p-5" key={candidate.candidate_id}><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="font-bold">{candidate.page_name}</h2><p className="text-sm text-zinc-500">Page ID {candidate.masked_page_id}</p>{candidate.instagram_username ? <p className="mt-1 text-sm">Instagram @{candidate.instagram_username} · {candidate.instagram_account_type}</p> : <p className="mt-1 text-sm text-amber-700">No professional Instagram account linked</p>}<p className={`mt-2 text-xs ${candidate.compatible ? "text-emerald-700" : "text-amber-700"}`}>{candidate.compatibility_message}</p></div><Button disabled={Boolean(pending)} onClick={() => select(candidate.candidate_id)}>{pending === candidate.candidate_id ? <><Loader2 className="animate-spin" /> Connecting...</> : "Select this Page"}</Button></div></article>)}{error ? <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}</div>;
}
