import {
  ArrowUpRight,
  Bell,
  CalendarClock,
  ChevronRight,
  CircleCheck,
  Clock3,
  Instagram,
  Linkedin,
  Menu,
  MoreHorizontal,
  Plus,
  Send,
  Sparkles,
  TrendingUp,
  Youtube,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { PlatformConnection, Publication, SocialPost, Workspace } from "@/lib/api";

export function Dashboard({
  connections,
  posts,
  publications,
  workspace,
}: {
  connections: PlatformConnection[];
  posts: SocialPost[];
  publications: Publication[];
  workspace: Workspace | null;
}) {
  const recentPosts = posts.slice(0, 3);
  const recentPublications = publications.slice(0, 4);
  const publishedCount = publications.filter((item) => item.status === "published").length;
  const scheduledCount = publications.filter((item) => item.status === "scheduled").length;

  return (
    <main className="min-h-screen bg-[#f8f8fa] lg:pl-64">
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-zinc-200/80 bg-white/85 px-5 backdrop-blur-xl sm:px-8">
        <div className="flex items-center gap-3">
          <button className="lg:hidden" aria-label="Open navigation">
            <Menu className="size-5" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-zinc-950">Overview</h1>
            <p className="hidden text-xs text-zinc-400 sm:block">
              SocialOS AI
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Notifications">
            <Bell className="size-4.5" />
          </Button>
          <Button>
            <Plus className="size-4" />
            Create post
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-[1440px] px-5 py-7 sm:px-8 sm:py-9">
        <section className="mb-8 flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="mb-1 text-sm font-medium text-violet-600">Good evening, Abdullah</p>
            <h2 className="max-w-xl text-2xl font-bold tracking-[-0.03em] text-zinc-950 sm:text-3xl">
              Your content engine is moving.
            </h2>
            <p className="mt-2 text-sm text-zinc-500">
              Here&apos;s what&apos;s happening across your social presence.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <CircleCheck className="size-4 text-emerald-500" />
            All systems operational
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Published"
            value={publishedCount.toString()}
            change="+12.4%"
            icon={<Send className="size-4.5" />}
            tone="violet"
          />
          <Metric
            label="Engagement"
            value="8.4%"
            change="+2.1%"
            icon={<TrendingUp className="size-4.5" />}
            tone="emerald"
          />
          <Metric
            label="Scheduled"
            value={scheduledCount.toString()}
            change="Next in 2h"
            icon={<CalendarClock className="size-4.5" />}
            tone="blue"
          />
          <Metric
            label="Time saved"
            value="18.5h"
            change="This month"
            icon={<Clock3 className="size-4.5" />}
            tone="amber"
          />
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[1.55fr_1fr]">
          <div className="overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-[0_1px_2px_rgba(0,0,0,.02)]">
            <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4 sm:px-6">
              <div>
                <h3 className="text-sm font-semibold text-zinc-950">Content performance</h3>
                <p className="mt-0.5 text-xs text-zinc-400">Last 30 days across all channels</p>
              </div>
              <button className="flex items-center gap-1 text-xs font-semibold text-zinc-500 hover:text-zinc-950">
                View analytics <ChevronRight className="size-3.5" />
              </button>
            </div>
            <div className="p-5 sm:p-6">
              <div className="mb-6 flex items-baseline gap-3">
                <span className="text-3xl font-bold tracking-tight text-zinc-950">
                  {workspace?.name ?? "Kinetic Mobiles"}
                </span>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-600">
                  +18.2%
                </span>
              </div>
              <PerformanceChart />
            </div>
          </div>

          <div className="rounded-2xl bg-zinc-950 p-6 text-white shadow-xl shadow-zinc-950/10">
            <div className="flex items-start justify-between">
              <div className="grid size-10 place-items-center rounded-xl bg-violet-500/20 text-violet-300">
                <Sparkles className="size-5" />
              </div>
              <span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
                AI insight
              </span>
            </div>
            <h3 className="mt-7 text-xl font-semibold tracking-tight">
              Your audience is most active on Tuesday mornings.
            </h3>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              Scheduling educational content between 9-11 AM could increase
              engagement by an estimated 24%.
            </p>
            <button className="mt-7 flex items-center gap-2 text-sm font-semibold text-violet-300 transition hover:text-violet-200">
              Optimize my schedule <ArrowUpRight className="size-4" />
            </button>
          </div>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[1.55fr_1fr]">
          <div className="rounded-2xl border border-zinc-200/80 bg-white">
            <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4 sm:px-6">
              <h3 className="text-sm font-semibold text-zinc-950">Recent content</h3>
              <button className="text-xs font-semibold text-violet-600 hover:text-violet-500">
                View all
              </button>
            </div>
            <div className="divide-y divide-zinc-100">
              {recentPublications.length > 0 ? (
                recentPublications.map((publication) => (
                  <PublicationRow key={publication.id} publication={publication} />
                ))
              ) : recentPosts.length > 0 ? (
                recentPosts.map((post) => (
                  <PostRow key={post.id} content={post.content} status={post.status} />
                ))
              ) : (
                <>
                  <PostRow
                    content="The future of marketing isn't more content. It's smarter systems."
                    status="published"
                  />
                  <PostRow
                    content="5 lessons from building a brand people remember"
                    status="scheduled"
                  />
                  <PostRow
                    content="Behind the scenes: how our team plans a launch"
                    status="draft"
                  />
                </>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200/80 bg-white p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-zinc-950">Connected channels</h3>
              <button className="text-xs font-semibold text-violet-600">Manage</button>
            </div>
            <div className="mt-5 space-y-3">
              {connections.length > 0 ? (
                connections.map((connection) => (
                  <Channel
                    key={connection.id}
                    icon={connection.platform === "instagram" ? <Instagram /> : <Send />}
                    name={connection.external_account_name}
                    detail={`${connection.provider} / ${connection.platform}`}
                    color={
                      connection.platform === "instagram"
                        ? "bg-pink-50 text-pink-600"
                        : "bg-blue-50 text-blue-600"
                    }
                  />
                ))
              ) : (
                <>
                  <Channel icon={<Instagram />} name="Instagram" detail="Ready for Meta OAuth" color="bg-pink-50 text-pink-600" />
                  <Channel icon={<Send />} name="Facebook Page" detail="Ready for Meta OAuth" color="bg-blue-50 text-blue-600" />
                  <Channel icon={<Linkedin />} name="LinkedIn" detail="Planned provider" color="bg-blue-50 text-blue-600" />
                  <Channel icon={<Youtube />} name="YouTube" detail="Planned provider" color="bg-red-50 text-red-600" />
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
  change,
  icon,
  tone,
}: {
  label: string;
  value: string;
  change: string;
  icon: React.ReactNode;
  tone: "violet" | "emerald" | "blue" | "amber";
}) {
  const tones = {
    violet: "bg-violet-50 text-violet-600",
    emerald: "bg-emerald-50 text-emerald-600",
    blue: "bg-blue-50 text-blue-600",
    amber: "bg-amber-50 text-amber-600",
  };
  return (
    <div className="rounded-2xl border border-zinc-200/80 bg-white p-5">
      <div className="flex items-center justify-between">
        <span className={`grid size-9 place-items-center rounded-xl ${tones[tone]}`}>{icon}</span>
        <span className="text-[11px] font-semibold text-zinc-400">{change}</span>
      </div>
      <p className="mt-5 text-2xl font-bold tracking-tight text-zinc-950">{value}</p>
      <p className="mt-1 text-xs font-medium text-zinc-500">{label}</p>
    </div>
  );
}

function PerformanceChart() {
  return (
    <div className="relative h-52 overflow-hidden">
      <div className="absolute inset-0 flex flex-col justify-between">
        {[0, 1, 2, 3].map((line) => (
          <div key={line} className="border-t border-dashed border-zinc-100" />
        ))}
      </div>
      <svg viewBox="0 0 700 210" className="absolute inset-0 size-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity=".22" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M0 173 C50 160 66 178 110 144 S180 153 225 117 S300 131 350 91 S430 112 475 68 S550 78 590 46 S660 58 700 24 V210 H0Z"
          fill="url(#area)"
        />
        <path
          d="M0 173 C50 160 66 178 110 144 S180 153 225 117 S300 131 350 91 S430 112 475 68 S550 78 590 46 S660 58 700 24"
          fill="none"
          stroke="#7c3aed"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex justify-between text-[10px] text-zinc-400">
        <span>Jun 20</span><span>Jun 27</span><span>Jul 04</span><span>Jul 11</span><span>Jul 19</span>
      </div>
    </div>
  );
}

function PostRow({ content, status }: { content: string; status: string }) {
  const statusStyle =
    status === "published"
      ? "bg-emerald-50 text-emerald-700"
      : status === "scheduled"
        ? "bg-blue-50 text-blue-700"
        : "bg-zinc-100 text-zinc-500";
  return (
    <div className="flex items-center gap-4 px-5 py-4 sm:px-6">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-violet-100 to-fuchsia-50 text-violet-600">
        <Sparkles className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-800">{content}</p>
        <p className="mt-1 text-[11px] text-zinc-400">Instagram / LinkedIn / X</p>
      </div>
      <span className={`hidden rounded-full px-2.5 py-1 text-[10px] font-bold capitalize sm:block ${statusStyle}`}>
        {status}
      </span>
      <button aria-label="Post actions"><MoreHorizontal className="size-4 text-zinc-400" /></button>
    </div>
  );
}

function PublicationRow({ publication }: { publication: Publication }) {
  const statusStyle =
    publication.status === "published"
      ? "bg-emerald-50 text-emerald-700"
      : publication.status === "failed_retryable" || publication.status === "failed_permanent"
        ? "bg-red-50 text-red-700"
        : publication.status === "scheduled" || publication.status === "queued"
          ? "bg-blue-50 text-blue-700"
          : "bg-zinc-100 text-zinc-500";
  return (
    <div className="flex items-center gap-4 px-5 py-4 sm:px-6">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-zinc-100 text-zinc-700">
        {publication.platform === "instagram" ? (
          <Instagram className="size-4" />
        ) : (
          <Send className="size-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-800">{publication.caption}</p>
        <p className="mt-1 truncate text-[11px] text-zinc-400">
          {publication.external_url ?? publication.last_error ?? publication.platform}
        </p>
      </div>
      <span className={`hidden rounded-full px-2.5 py-1 text-[10px] font-bold capitalize sm:block ${statusStyle}`}>
        {publication.status.replace("_", " ")}
      </span>
      {publication.external_url ? (
        <a aria-label="Open published post" href={publication.external_url} rel="noreferrer" target="_blank">
          <ArrowUpRight className="size-4 text-zinc-400" />
        </a>
      ) : (
        <button aria-label="Publication actions"><MoreHorizontal className="size-4 text-zinc-400" /></button>
      )}
    </div>
  );
}

function Channel({
  icon,
  name,
  detail,
  color,
}: {
  icon: React.ReactNode;
  name: string;
  detail: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-100 p-3">
      <span className={`grid size-9 place-items-center rounded-lg [&>svg]:size-4 ${color}`}>{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-zinc-800">{name}</p>
        <p className="mt-0.5 text-[10px] text-zinc-400">{detail}</p>
      </div>
      <span className="size-2 rounded-full bg-emerald-400 ring-4 ring-emerald-50" />
    </div>
  );
}
