import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

import { Dashboard } from "@/components/dashboard";
import { DemoDashboard } from "@/components/demo/demo-dashboard";
import { Sidebar } from "@/components/sidebar";
import {
  ensureWorkspace,
  getProviderCatalog,
  getPublication,
  listBrandProfiles,
  listCampaigns,
  listContentItems,
  listMediaAssets,
  listPlatformConnections,
  listPosts,
  listPublications,
  listSocialAccounts,
  type ProviderCatalog,
} from "@/lib/api";

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<{
    publication?: string;
    notice?: string;
    aiCost?: string;
  }>;
}) {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return <DemoDashboard />;
  }

  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    const { orgId } = await auth.protect();
    if (!orgId) redirect("/onboarding");
  }

  const [posts, workspace] = await Promise.all([
    listPosts(),
    ensureWorkspace(),
  ]);
  const [connections, publications] = workspace
    ? await Promise.all([
        listPlatformConnections(workspace.id),
        listPublications(workspace.id),
      ])
    : [[], []];
  const [brands, campaigns, contentItems, mediaAssets, socialAccounts, providerCatalog] =
    workspace
      ? await Promise.all([
          listBrandProfiles(workspace.id),
          listCampaigns(workspace.id),
          listContentItems(workspace.id),
          listMediaAssets(workspace.id),
          listSocialAccounts(workspace.id),
          getProviderCatalog(workspace.id).catch((): ProviderCatalog => ({ items: [] })),
        ])
      : [[], [], [], [], [], { items: [] }];
  const params = await searchParams;
  const selectedPublication =
    publications.find(
      (publication) => publication.id === params?.publication,
    ) ??
    publications[0] ??
    null;
  const publicationDetail = selectedPublication
    ? await getPublication(selectedPublication.id)
    : null;

  return (
    <>
      <Sidebar />
      <Dashboard
        brands={brands}
        campaigns={campaigns}
        connections={connections}
        contentItems={contentItems}
        mediaAssets={mediaAssets}
        aiCost={params?.aiCost ?? null}
        notice={params?.notice ?? null}
        posts={posts}
        publicationDetail={publicationDetail}
        providerCatalog={providerCatalog}
        publications={publications}
        socialAccounts={socialAccounts}
        socialProvider={process.env.SOCIAL_PROVIDER === "meta" ? "meta" : "local-dev"}
        workspace={workspace}
      />
    </>
  );
}
