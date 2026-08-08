import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("next security headers", () => {
  it("applies baseline browser hardening headers to every route", async () => {
    expect(nextConfig.poweredByHeader).toBe(false);
    expect(nextConfig.experimental?.serverActions?.bodySizeLimit).toBe("16mb");

    const headers = await nextConfig.headers?.();

    expect(headers).toContainEqual({
      source: "/(.*)",
      headers: expect.arrayContaining([
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        {
          key: "Permissions-Policy",
          value: "camera=(), microphone=(), geolocation=()",
        },
      ]),
    });
  });
});
