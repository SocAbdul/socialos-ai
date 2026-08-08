import type { PlatformConnection, SocialAccount } from "@/lib/api";

export type SocialProviderMode = "local-dev" | "meta";

export function accountsForProvider(
  accounts: SocialAccount[],
  connections: PlatformConnection[],
  provider: SocialProviderMode,
): SocialAccount[] {
  const connectionIds = new Set(
    connections
      .filter((connection) => connection.provider === provider)
      .map((connection) => connection.id),
  );
  return accounts.filter(
    (account) =>
      account.active && connectionIds.has(account.platform_connection_id),
  );
}
