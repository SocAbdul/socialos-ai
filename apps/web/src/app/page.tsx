import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { Dashboard } from "@/components/dashboard";
import { DemoDashboard } from "@/components/demo/demo-dashboard";
import { Sidebar } from "@/components/sidebar";
import { ensureWorkspace, listPlatformConnections, listPosts, listPublications } from "@/lib/api";

export default async function Home() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return <DemoDashboard />;
  }

  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    const { orgId } = await auth.protect();
    if (!orgId) redirect("/onboarding");
  }

  const [posts, workspace] = await Promise.all([listPosts(), ensureWorkspace()]);
  const [connections, publications] = workspace
    ? await Promise.all([
        listPlatformConnections(workspace.id),
        listPublications(workspace.id),
      ])
    : [[], []];

  return (
    <>
      <Sidebar />
      <Dashboard
        connections={connections}
        posts={posts}
        publications={publications}
        workspace={workspace}
      />
    </>
  );
}
