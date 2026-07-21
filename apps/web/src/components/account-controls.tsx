"use client";

import { OrganizationSwitcher, UserButton } from "@clerk/nextjs";

export function AccountControls({ clerkEnabled }: { clerkEnabled: boolean }) {
  if (!clerkEnabled) {
    return (
      <>
        <div className="grid size-9 place-items-center rounded-full bg-zinc-900 text-xs font-bold text-white">
          AF
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-zinc-900">Local founder</p>
          <p className="truncate text-[11px] text-zinc-500">Development mode</p>
        </div>
      </>
    );
  }

  return (
    <div className="flex w-full items-center gap-3">
      <UserButton />
      <OrganizationSwitcher
        hidePersonal
        afterCreateOrganizationUrl="/"
        afterSelectOrganizationUrl="/"
        appearance={{
          elements: {
            rootBox: "min-w-0 flex-1",
            organizationSwitcherTrigger: "w-full",
          },
        }}
      />
    </div>
  );
}

