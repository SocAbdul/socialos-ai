"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

import { DashboardLink, FullPageState, ReloadButton } from "@/components/full-page-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled application error", {
      digest: error.digest,
      message: error.message,
    });
  }, [error]);

  return (
    <FullPageState
      badge="Something needs attention"
      title="SocialOS hit an unexpected error."
      description="Your workspace data is safe. Try reloading this view, or return to the dashboard while we recover the page."
      icon={AlertTriangle}
      primaryAction={<ReloadButton onClick={reset} />}
      secondaryAction={<DashboardLink />}
    />
  );
}
