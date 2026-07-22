import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

const API_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

const developmentIdentity = {
  "X-User-Id": "user_local_founder",
  "X-Organization-Id": "org_local_socialos",
  "X-Organization-Role": "org:admin",
};

type CallbackSearchParams = {
  code?: string | string[];
  state?: string | string[];
  error?: string | string[];
  error_description?: string | string[];
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

async function authenticationHeaders(): Promise<Record<string, string>> {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return developmentIdentity;
  }

  const { getToken, orgId } = await auth();
  if (!orgId) throw new Error("Select an organization before connecting Meta.");
  const token = await getToken();
  if (!token) throw new Error("Your session expired. Sign in and connect Meta again.");
  return { Authorization: `Bearer ${token}` };
}

function responseDetail(payload: unknown): string | null {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return null;
  }
  const detail = (payload as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : null;
}

function CallbackResult({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f8fa] p-6">
      <div className="w-full max-w-lg rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-violet-600">
          Meta connection
        </p>
        <h1 className="mt-3 text-2xl font-bold text-zinc-950">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-600">{message}</p>
        <Link
          className="mt-6 inline-flex rounded-xl bg-zinc-950 px-4 py-2.5 text-sm font-semibold text-white"
          href="/"
        >
          Return to dashboard
        </Link>
      </div>
    </main>
  );
}

export default async function MetaCallbackPage({
  searchParams,
}: {
  searchParams: Promise<CallbackSearchParams>;
}) {
  const params = await searchParams;
  const providerError = first(params.error_description) ?? first(params.error);
  if (providerError) {
    return <CallbackResult title="Meta connection cancelled" message={providerError} />;
  }

  const code = first(params.code);
  const state = first(params.state);
  if (!code || !state) {
    return (
      <CallbackResult
        title="Meta callback is incomplete"
        message="The authorization code or security state is missing. Start the connection again."
      />
    );
  }

  let failureMessage: string | null = null;

  try {
    const headers = await authenticationHeaders();
    const response = await fetch(`${API_URL}/platform-connections/meta/callback`, {
      method: "POST",
      headers,
      body: JSON.stringify({ code, state }),
      cache: "no-store",
    });

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      failureMessage =
        responseDetail(payload) ?? "The backend rejected the Meta connection.";
    }
  } catch (error) {
    failureMessage =
      error instanceof Error ? error.message : "The connection could not be completed.";
  }

  if (failureMessage) {
    return (
      <CallbackResult
        title="Meta connection failed"
        message={failureMessage}
      />
    );
  }

  redirect("/?meta=connected");
}
