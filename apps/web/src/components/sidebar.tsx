"use client";

import {
  BarChart3,
  CalendarDays,
  CircleHelp,
  Files,
  LayoutDashboard,
  Megaphone,
  Menu,
  Settings,
  Sparkles,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { useState } from "react";

import { AccountControls } from "@/components/account-controls";
import { Button } from "@/components/ui/button";

type NavigationItem = {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href?: "#overview" | "#create-post";
};

const primary: NavigationItem[] = [
  { label: "Overview", icon: LayoutDashboard, href: "#overview" },
  { label: "Create", icon: Sparkles, href: "#create-post" },
  { label: "Content", icon: Files },
  { label: "Calendar", icon: CalendarDays },
  { label: "Analytics", icon: BarChart3 },
];

const workspace: NavigationItem[] = [
  { label: "Campaigns", icon: Megaphone },
  { label: "Automations", icon: Workflow },
  { label: "Team", icon: Users },
];

const support: NavigationItem[] = [
  { label: "Help center", icon: CircleHelp },
  { label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-zinc-200/80 bg-white lg:flex">
      <SidebarContent />
    </aside>
  );
}

export function MobileNavigation() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        aria-controls="mobile-navigation"
        aria-expanded={open}
        aria-label="Open navigation"
        className="lg:hidden"
        onClick={() => setOpen(true)}
        size="icon"
        variant="ghost"
      >
        <Menu className="size-5" />
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-label="Navigation"
        >
          <button
            aria-label="Close navigation overlay"
            className="absolute inset-0 bg-zinc-950/35 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            type="button"
          />
          <aside
            className="relative flex h-full w-[min(20rem,86vw)] flex-col bg-white shadow-2xl"
            id="mobile-navigation"
          >
            <Button
              aria-label="Close navigation"
              className="absolute right-3 top-3"
              onClick={() => setOpen(false)}
              size="icon"
              variant="ghost"
            >
              <X className="size-5" />
            </Button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      ) : null}
    </>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const [activeHref, setActiveHref] =
    useState<NavigationItem["href"]>("#overview");
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  const navigate = (href: NavigationItem["href"]) => {
    setActiveHref(href);
    onNavigate?.();
  };

  return (
    <>
      <div className="flex h-16 items-center gap-3 px-5">
        <div className="grid size-9 place-items-center rounded-xl bg-zinc-950 text-white shadow-sm">
          <Sparkles className="size-4.5" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-zinc-950">
            SocialOS
          </p>
          <p className="text-[10px] font-semibold tracking-[0.18em] text-violet-600 uppercase">
            AI workspace
          </p>
        </div>
      </div>

      <div className="mx-3 mt-2 flex items-center gap-3 rounded-xl border border-zinc-200 p-2.5">
        <div className="grid size-8 place-items-center rounded-lg bg-amber-100 text-xs font-bold text-amber-800">
          KM
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-zinc-900">
            Kinetic Mobiles
          </p>
          <p className="text-[11px] text-zinc-500">Local workspace</p>
        </div>
      </div>

      <nav
        aria-label="Main navigation"
        className="flex-1 space-y-7 overflow-y-auto px-3 py-6"
      >
        <NavGroup
          activeHref={activeHref}
          items={primary}
          onNavigate={navigate}
        />
        <div>
          <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.16em] text-zinc-400 uppercase">
            Workspace
          </p>
          <NavGroup
            activeHref={activeHref}
            items={workspace}
            onNavigate={navigate}
          />
        </div>
      </nav>

      <div className="space-y-1 border-t border-zinc-100 p-3">
        <NavGroup
          activeHref={activeHref}
          items={support}
          onNavigate={navigate}
        />
        <div className="mt-3 flex items-center gap-3 rounded-xl p-2">
          <AccountControls clerkEnabled={clerkEnabled} />
        </div>
      </div>
    </>
  );
}

function NavGroup({
  activeHref,
  items,
  onNavigate,
}: {
  activeHref: NavigationItem["href"];
  items: NavigationItem[];
  onNavigate: (href: NavigationItem["href"]) => void;
}) {
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <NavItem
          active={Boolean(item.href && item.href === activeHref)}
          item={item}
          key={item.label}
          onNavigate={onNavigate}
        />
      ))}
    </div>
  );
}

function NavItem({
  active,
  item,
  onNavigate,
}: {
  active: boolean;
  item: NavigationItem;
  onNavigate: (href: NavigationItem["href"]) => void;
}) {
  const Icon = item.icon;
  const classes = `flex min-h-11 w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${
    active
      ? "bg-violet-50 text-violet-700"
      : item.href
        ? "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900"
        : "cursor-not-allowed text-zinc-400"
  }`;

  if (item.href) {
    return (
      <a
        aria-current={active ? "page" : undefined}
        className={classes}
        href={item.href}
        onClick={() => onNavigate(item.href)}
      >
        <Icon className="size-4.5" />
        <span className="flex-1">{item.label}</span>
      </a>
    );
  }

  return (
    <span
      aria-disabled="true"
      className={classes}
      title={`${item.label} is coming soon`}
    >
      <Icon className="size-4.5" />
      <span className="flex-1">{item.label}</span>
      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[9px] font-bold tracking-wide text-zinc-500 uppercase">
        Coming soon
      </span>
    </span>
  );
}
