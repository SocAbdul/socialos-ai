import Link from "next/link";

import { getMetaOAuthSession } from "@/lib/api";
import { MetaSelection } from "./selection";

export default async function MetaSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const session = await getMetaOAuthSession(sessionId);
  return <main className="min-h-screen bg-[#f8f8fa] p-5 sm:p-8"><div className="mx-auto max-w-3xl"><Link className="text-sm font-semibold text-violet-700" href="/integrations">← Connected accounts</Link><h1 className="mt-6 text-3xl font-bold">Choose the Page to connect</h1><p className="mb-6 mt-2 text-zinc-600">Select by name and linked Instagram account. SocialOS never displays access tokens or permission internals here.</p><MetaSelection session={session} /></div></main>;
}
