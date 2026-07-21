import {
  BarChart3,
  CalendarDays,
  ChevronDown,
  CircleHelp,
  Files,
  LayoutDashboard,
  Megaphone,
  Settings,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";

import { AccountControls } from "@/components/account-controls";

const primary = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Create", icon: Sparkles },
  { label: "Content", icon: Files },
  { label: "Calendar", icon: CalendarDays },
  { label: "Analytics", icon: BarChart3 },
];

const workspace = [
  { label: "Campaigns", icon: Megaphone },
  { label: "Automations", icon: Workflow },
  { label: "Team", icon: Users },
];

export function Sidebar() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-zinc-200/80 bg-white lg:flex">
      <div className="flex h-16 items-center gap-3 px-5">
        <div className="grid size-9 place-items-center rounded-xl bg-zinc-950 text-white shadow-sm">
          <Sparkles className="size-4.5" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-zinc-950">SocialOS</p>
          <p className="text-[10px] font-semibold tracking-[0.18em] text-violet-600 uppercase">
            AI workspace
          </p>
        </div>
      </div>

      <div className="mx-3 mt-2 flex items-center gap-3 rounded-xl border border-zinc-200 p-2.5">
        <div className="grid size-8 place-items-center rounded-lg bg-amber-100 text-xs font-bold text-amber-800">
          AC
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-zinc-900">Acme Studio</p>
          <p className="text-[11px] text-zinc-500">Business plan</p>
        </div>
        <ChevronDown className="size-4 text-zinc-400" />
      </div>

      <nav className="flex-1 space-y-7 px-3 py-6">
        <NavGroup items={primary} />
        <div>
          <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.16em] text-zinc-400 uppercase">
            Workspace
          </p>
          <NavGroup items={workspace} />
        </div>
      </nav>

      <div className="space-y-1 border-t border-zinc-100 p-3">
        <NavItem label="Help center" icon={CircleHelp} />
        <NavItem label="Settings" icon={Settings} />
        <div className="mt-3 flex items-center gap-3 rounded-xl p-2">
          <AccountControls clerkEnabled={clerkEnabled} />
        </div>
      </div>
    </aside>
  );
}

function NavGroup({
  items,
}: {
  items: Array<{
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    active?: boolean;
  }>;
}) {
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <NavItem key={item.label} {...item} />
      ))}
    </div>
  );
}

function NavItem({
  label,
  icon: Icon,
  active,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${
        active
          ? "bg-violet-50 text-violet-700"
          : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
      }`}
    >
      <Icon className="size-4.5" />
      {label}
    </button>
  );
}
