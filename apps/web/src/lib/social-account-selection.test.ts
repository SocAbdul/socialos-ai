import { describe, expect, it } from "vitest";

import type { PlatformConnection, SocialAccount } from "./api";
import { accountsForProvider } from "./social-account-selection";

const connections = [
  { id: "meta-connection", provider: "meta" },
  { id: "local-connection", provider: "local-dev" },
] as PlatformConnection[];

const accounts = [
  {
    id: "meta-facebook",
    platform_connection_id: "meta-connection",
    platform: "facebook",
    active: true,
  },
  {
    id: "local-facebook",
    platform_connection_id: "local-connection",
    platform: "facebook",
    active: true,
  },
  {
    id: "inactive-meta-instagram",
    platform_connection_id: "meta-connection",
    platform: "instagram",
    active: false,
  },
] as SocialAccount[];

describe("accountsForProvider", () => {
  it("returns only active accounts belonging to real Meta connections", () => {
    expect(accountsForProvider(accounts, connections, "meta").map(({ id }) => id)).toEqual([
      "meta-facebook",
    ]);
  });

  it("keeps local development accounts isolated", () => {
    expect(
      accountsForProvider(accounts, connections, "local-dev").map(({ id }) => id),
    ).toEqual(["local-facebook"]);
  });
});
