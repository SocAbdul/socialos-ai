import Link from "next/link";

export function AuthDisabled() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f8fa] p-6">
      <div className="max-w-md space-y-3 rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-violet-600">SocialOS AI</p>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-950">
          Local development mode
        </h1>
        <p className="text-sm leading-6 text-zinc-500">
          Clerk is disabled. Add the Clerk environment variables to exercise
          sign-in and organization onboarding.
        </p>
        <Link
          className="inline-flex rounded-lg bg-zinc-950 px-4 py-2 text-sm font-semibold text-white"
          href="/"
        >
          Open dashboard
        </Link>
      </div>
    </main>
  );
}
