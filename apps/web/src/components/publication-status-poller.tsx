"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function PublicationStatusPoller({ status }: { status: string }) {
  const router = useRouter();
  const shouldPoll = status === "queued" || status === "publishing";

  useEffect(() => {
    if (!shouldPoll) return;

    const interval = window.setInterval(() => router.refresh(), 1_500);
    return () => window.clearInterval(interval);
  }, [router, shouldPoll]);

  if (!shouldPoll) return null;

  return (
    <p
      aria-live="polite"
      className="mt-2 text-xs font-medium text-blue-700"
      role="status"
    >
      {status === "queued"
        ? "Queued for the local worker. Checking delivery status..."
        : "The local worker is publishing. Checking delivery status..."}
    </p>
  );
}
