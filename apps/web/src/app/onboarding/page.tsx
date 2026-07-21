import { OrganizationList } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { AuthDisabled } from "@/components/auth-disabled";

export default async function OnboardingPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <AuthDisabled />;
  }

  const { orgId } = await auth.protect();
  if (orgId) redirect("/");

  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f8fa] p-6">
      <div className="space-y-6 text-center">
        <div>
          <p className="text-sm font-semibold text-violet-600">SocialOS AI</p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-zinc-950">
            Choose your workspace
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            Create or select an organization to continue.
          </p>
        </div>
        <OrganizationList
          hidePersonal
          afterCreateOrganizationUrl="/"
          afterSelectOrganizationUrl="/"
        />
      </div>
    </main>
  );
}
