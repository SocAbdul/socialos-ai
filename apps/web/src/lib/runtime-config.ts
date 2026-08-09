import "server-only";

export function apiInternalUrl(): string {
  const configured = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (configured) return configured.replace(/\/$/, "");
  return process.env.NODE_ENV === "production"
    ? "http://api:8000/api/v1"
    : "http://localhost:8000/api/v1";
}
