"use client";

import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Facebook,
  ImageIcon,
  Instagram,
  Loader2,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  adaptCaption,
  createDemoPublications,
  initialDraft,
  loadDemoState,
  resetDemoState,
  retryDemoPublication,
  saveDemoState,
  settleRetry,
} from "@/lib/demo/repository";
import type { DemoComposerDraft, DemoPlatform, DemoPublication, DemoState } from "@/lib/demo/types";

const platformLabels = {
  facebook: "Facebook",
  instagram: "Instagram",
} satisfies Record<DemoPlatform, string>;

export function DemoDashboard() {
  const [state, setState] = useState<DemoState | null>(null);
  const [draft, setDraft] = useState<DemoComposerDraft>(initialDraft);
  const [selectedPublicationId, setSelectedPublicationId] = useState<string | null>(null);
  const [isAdapting, setIsAdapting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setState(loadDemoState()), 250);
    return () => window.clearTimeout(timer);
  }, []);

  const selectedPublication = useMemo(
    () => state?.publications.find((item) => item.id === selectedPublicationId) ?? null,
    [selectedPublicationId, state],
  );

  if (!state) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f8f8fa]">
        <div className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-600">
          <Loader2 className="size-4 animate-spin" />
          Loading Kinetic Mobiles demo...
        </div>
      </main>
    );
  }

  function persist(next: DemoState) {
    setState(next);
    saveDemoState(next);
  }

  function adapt() {
    setIsAdapting(true);
    window.setTimeout(() => {
      setDraft((current) => ({
        ...current,
        facebookCaption: adaptCaption(current.originalText, "facebook"),
        instagramCaption: adaptCaption(current.originalText, "instagram"),
      }));
      setIsAdapting(false);
      setSuccessMessage("Adapted copy is ready for both platforms.");
    }, 450);
  }

  function publish(status: "published" | "scheduled") {
    if (!state) return;
    const next = createDemoPublications(state, draft, status);
    persist(next);
    setSelectedPublicationId(next.publications[0]?.id ?? null);
    setSuccessMessage(status === "published" ? "Publication sent successfully." : "Publication scheduled.");
  }

  function retry(publication: DemoPublication) {
    if (!state) return;
    const retrying = retryDemoPublication(state, publication.id);
    persist(retrying);
    window.setTimeout(() => {
      const settled = settleRetry(retrying, publication.id);
      persist(settled);
      setSuccessMessage("Retry completed without creating a duplicate.");
    }, 700);
  }

  function reset() {
    const next = resetDemoState();
    setState(next);
    setDraft(initialDraft);
    setSelectedPublicationId(null);
    setSuccessMessage("Demo reset to the original Kinetic Mobiles data.");
  }

  const published = state.publications.filter((item) => item.status === "published").length;
  const scheduled = state.publications.filter((item) => item.status === "scheduled").length;
  const needsAttention = state.publications.filter((item) =>
    ["failed", "uncertain"].includes(item.status),
  ).length;

  return (
    <main className="min-h-screen bg-[#f8f8fa] text-zinc-950">
      <div className="mx-auto grid max-w-[1500px] gap-6 px-4 py-5 lg:grid-cols-[280px_1fr] lg:px-6">
        <aside className="rounded-lg border border-zinc-200 bg-white p-4 lg:sticky lg:top-5 lg:h-[calc(100vh-40px)]">
          <div className="flex items-center gap-3">
            <div className="grid size-9 place-items-center rounded-lg bg-zinc-950 text-white">
              <Sparkles className="size-4" />
            </div>
            <div>
              <p className="text-sm font-semibold">SocialOS AI</p>
              <p className="text-xs text-zinc-500">Kinetic Mobiles demo</p>
            </div>
          </div>

          <nav className="mt-7 space-y-1 text-sm">
            {["Dashboard", "Connections", "Composer", "Publications"].map((item) => (
              <a
                className="block rounded-md px-3 py-2 font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"
                href={`#${item.toLowerCase()}`}
                key={item}
              >
                {item}
              </a>
            ))}
          </nav>

          <Button className="mt-7 w-full" onClick={reset} variant="outline">
            <RotateCcw className="size-4" />
            Reset demo
          </Button>
        </aside>

        <section className="space-y-6">
          <header id="dashboard" className="rounded-lg border border-zinc-200 bg-white p-5">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Demo mode</p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight">Review the Meta publishing flow</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
                  Connect mock Meta accounts, compose a Kinetic Mobiles post, adapt it for Facebook and Instagram, then publish or schedule it.
                </p>
              </div>
              <Button onClick={() => document.getElementById("composer")?.scrollIntoView()}>
                <Send className="size-4" />
                Create publication
              </Button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <Metric icon={<CheckCircle2 />} label="Published" value={published.toString()} />
              <Metric icon={<CalendarClock />} label="Scheduled" value={scheduled.toString()} />
              <Metric icon={<AlertCircle />} label="Needs review" value={needsAttention.toString()} />
            </div>
          </header>

          {successMessage ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
              {successMessage}
            </div>
          ) : null}

          <section id="connections" className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
            <Panel title="Social connection" subtitle="Mocked locally, isolated from real Meta credentials.">
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="grid size-10 place-items-center rounded-lg bg-blue-50 text-blue-600">
                      <Facebook className="size-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Meta connection</p>
                      <p className="text-xs text-zinc-500">Facebook Page + Instagram Business</p>
                    </div>
                  </div>
                  <StatusBadge status="published" label="Connected" />
                </div>
              </div>
            </Panel>

            <Panel title="Discovered accounts" subtitle="Capabilities are evaluated per account.">
              <div className="grid gap-3 md:grid-cols-2">
                {state.accounts.map((account) => (
                  <AccountCard account={account} key={account.id} />
                ))}
              </div>
            </Panel>
          </section>

          <section id="composer" className="grid gap-4 xl:grid-cols-[1fr_420px]">
            <Panel title="Composer" subtitle="Create once, adapt for each platform.">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    Original text
                  </label>
                  <textarea
                    className="mt-2 min-h-32 w-full resize-y rounded-lg border border-zinc-200 bg-white px-3 py-3 text-sm leading-6 outline-none focus:border-zinc-400"
                    value={draft.originalText}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, originalText: event.target.value }))
                    }
                  />
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Platforms</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(["facebook", "instagram"] as DemoPlatform[]).map((platform) => (
                      <button
                        className={`rounded-md border px-3 py-2 text-sm font-semibold ${
                          draft.selectedPlatforms.includes(platform)
                            ? "border-zinc-950 bg-zinc-950 text-white"
                            : "border-zinc-200 bg-white text-zinc-700"
                        }`}
                        key={platform}
                        onClick={() =>
                          setDraft((current) => ({
                            ...current,
                            selectedPlatforms: current.selectedPlatforms.includes(platform)
                              ? current.selectedPlatforms.filter((item) => item !== platform)
                              : [...current.selectedPlatforms, platform],
                          }))
                        }
                        type="button"
                      >
                        {platformLabels[platform]}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-4">
                  <div className="flex items-center gap-3">
                    <ImageIcon className="size-5 text-zinc-500" />
                    <div>
                      <p className="text-sm font-semibold">{draft.imageName}</p>
                      <p className="text-xs text-zinc-500">Simulated upload, HTTPS-ready media asset</p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button onClick={adapt} variant="outline">
                    {isAdapting ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                    Adapt copy
                  </Button>
                  <Button onClick={() => publish("published")}>
                    <Send className="size-4" />
                    Publish now
                  </Button>
                  <Button onClick={() => publish("scheduled")} variant="outline">
                    <Clock3 className="size-4" />
                    Schedule
                  </Button>
                </div>
              </div>
            </Panel>

            <Panel title="Platform previews" subtitle="What the post will look like before sending.">
              <div className="space-y-3">
                <PreviewCard caption={draft.facebookCaption} platform="facebook" />
                <PreviewCard caption={draft.instagramCaption} platform="instagram" />
              </div>
            </Panel>
          </section>

          <section id="publications" className="grid gap-4 xl:grid-cols-[1fr_420px]">
            <Panel title="Publications" subtitle="Review status, external URL, and retries.">
              <div className="divide-y divide-zinc-100">
                {state.publications.length === 0 ? (
                  <div className="py-10 text-center text-sm text-zinc-500">
                    No publications yet. Create your first Kinetic Mobiles post above.
                  </div>
                ) : (
                  state.publications.map((publication) => (
                    <button
                      className="flex w-full items-center justify-between gap-4 py-4 text-left"
                      key={publication.id}
                      onClick={() => setSelectedPublicationId(publication.id)}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">{publication.caption}</p>
                        <p className="mt-1 text-xs text-zinc-500">
                          {platformLabels[publication.platform]} / {publication.imageName ?? "No image"}
                        </p>
                      </div>
                      <StatusBadge status={publication.status} />
                    </button>
                  ))
                )}
              </div>
            </Panel>

            <Panel title="Publication detail" subtitle="Clear next action for every state.">
              {selectedPublication ? (
                <PublicationDetail publication={selectedPublication} onRetry={() => retry(selectedPublication)} />
              ) : (
                <div className="rounded-lg border border-dashed border-zinc-300 p-5 text-sm text-zinc-500">
                  Select a publication to inspect status, error details, and retry options.
                </div>
              )}
            </Panel>
          </section>
        </section>
      </div>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
      <div className="flex items-center justify-between">
        <span className="text-zinc-500 [&>svg]:size-4">{icon}</span>
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="mt-2 text-xs font-semibold text-zinc-500">{label}</p>
    </div>
  );
}

function Panel({ children, subtitle, title }: { children: React.ReactNode; subtitle: string; title: string }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-5">
      <div className="mb-4">
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function AccountCard({ account }: { account: DemoState["accounts"][number] }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-lg bg-zinc-100 text-zinc-700">
            {account.platform === "instagram" ? <Instagram className="size-4" /> : <Facebook className="size-4" />}
          </div>
          <div>
            <p className="text-sm font-semibold">{account.displayName}</p>
            <p className="text-xs text-zinc-500">{account.username ?? account.accountType}</p>
          </div>
        </div>
        <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">
          Active
        </span>
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        {account.capabilities.supportsText ? "Text" : "No text-only"} / Single image / {account.capabilities.maxTextLength} chars
      </p>
    </div>
  );
}

function PreviewCard({ caption, platform }: { caption: string; platform: DemoPlatform }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        {platform === "instagram" ? <Instagram className="size-4" /> : <Facebook className="size-4" />}
        {platformLabels[platform]} preview
      </div>
      <div className="aspect-[1.6] rounded-md bg-gradient-to-br from-zinc-200 via-zinc-100 to-white p-3">
        <div className="grid size-full place-items-center rounded border border-white/80 bg-white/55 text-xs font-semibold text-zinc-500">
          Kinetic Mobiles repair bench
        </div>
      </div>
      <p className="mt-3 whitespace-pre-line text-sm leading-6 text-zinc-700">{caption}</p>
    </div>
  );
}

function PublicationDetail({
  onRetry,
  publication,
}: {
  onRetry: () => void;
  publication: DemoPublication;
}) {
  const nextAction =
    publication.status === "failed"
      ? "Fix the issue and retry publishing."
      : publication.status === "uncertain"
        ? "Reconcile with Meta before retrying to avoid duplicates."
        : publication.status === "scheduled"
          ? "This will publish at the scheduled time."
          : publication.status === "published"
            ? "Open the external URL to verify the result."
            : "SocialOS is processing this publication.";

  return (
    <div className="space-y-4">
      <StatusBadge status={publication.status} />
      <p className="text-sm leading-6 text-zinc-700">{publication.caption}</p>
      <div className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-600">{nextAction}</div>
      {publication.error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {publication.error}
        </div>
      ) : null}
      {publication.externalUrl ? (
        <a className="text-sm font-semibold text-blue-600 hover:text-blue-500" href={publication.externalUrl}>
          Open external publication
        </a>
      ) : null}
      {publication.status === "failed" || publication.status === "uncertain" ? (
        <Button onClick={onRetry} variant="outline">
          <RefreshCw className="size-4" />
          Retry safely
        </Button>
      ) : null}
    </div>
  );
}

function StatusBadge({ label, status }: { label?: string; status: DemoPublication["status"] }) {
  const styles = {
    draft: "bg-zinc-100 text-zinc-700",
    scheduled: "bg-blue-50 text-blue-700",
    publishing: "bg-amber-50 text-amber-700",
    published: "bg-emerald-50 text-emerald-700",
    uncertain: "bg-purple-50 text-purple-700",
    failed: "bg-red-50 text-red-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-bold capitalize ${styles[status]}`}>
      {label ?? status}
    </span>
  );
}
