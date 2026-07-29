import Link from "next/link";
import type { ComponentType, ReactNode } from "react";
import { ArrowLeft, RefreshCw, ShieldAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type FullPageStateProps = {
  badge: string;
  title: string;
  description: string;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
  icon?: ComponentType<{ className?: string }>;
  className?: string;
};

export function FullPageState({
  badge,
  title,
  description,
  primaryAction,
  secondaryAction,
  icon: Icon = ShieldAlert,
  className,
}: FullPageStateProps) {
  return (
    <main
      className={cn(
        "grid min-h-screen place-items-center bg-[radial-gradient(circle_at_top_left,#ede9fe,transparent_34%),#f8f8fa] px-5 py-12",
        className,
      )}
    >
      <section className="w-full max-w-xl rounded-[2rem] border border-white/70 bg-white/90 p-6 text-center shadow-2xl shadow-zinc-950/10 backdrop-blur sm:p-10">
        <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-violet-50 text-violet-600 ring-8 ring-violet-50/40">
          <Icon className="size-6" />
        </div>
        <p className="mt-7 text-xs font-bold tracking-[0.28em] text-violet-600 uppercase">
          {badge}
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-[-0.04em] text-zinc-950 sm:text-4xl">
          {title}
        </h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-zinc-500">
          {description}
        </p>
        {(primaryAction || secondaryAction) && (
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            {primaryAction}
            {secondaryAction}
          </div>
        )}
      </section>
    </main>
  );
}

export function DashboardLink() {
  return (
    <Button asChild>
      <Link href="/">
        <ArrowLeft className="size-4" />
        Back to dashboard
      </Link>
    </Button>
  );
}

export function ReloadButton({ onClick }: { onClick: () => void }) {
  return (
    <Button onClick={onClick} variant="outline">
      <RefreshCw className="size-4" />
      Try again
    </Button>
  );
}
