import { describe, expect, it } from "vitest";

import {
  completeMetaSelection,
  createMetaCompletionGuard,
  isTrustedMetaPopupMessage,
  META_OAUTH_COMPLETION_TYPE,
  shouldOfferPopupContinuation,
  validateMetaAuthorizationUrl,
} from "./meta-oauth-client";

const validUrl = "https://www.facebook.com/v25.0/dialog/oauth?client_id=app&redirect_uri=https%3A%2F%2Fapp.test%2Fintegrations%2Fmeta%2Fcallback&state=state&config_id=config&response_type=code";

describe("Meta OAuth browser security", () => {
  it("accepts the expected Facebook Login for Business URL", () => {
    expect(validateMetaAuthorizationUrl(validUrl)).toContain("config_id=config");
  });

  it.each([
    "http://www.facebook.com/v25.0/dialog/oauth?config_id=x&response_type=code",
    "https://facebook.com/v25.0/dialog/oauth?config_id=x&response_type=code",
    "https://user:password@www.facebook.com/v25.0/dialog/oauth?config_id=x&response_type=code",
    "https://www.facebook.com/v25.0/dialog/oauth?response_type=code",
    "https://www.facebook.com/v25.0/dialog/oauth?config_id=x&response_type=token",
    "https://www.facebook.com/v25.0/dialog/oauth?config_id=x&response_type=code&scope=email",
  ])("rejects an unsafe authorization URL: %s", (url) => {
    expect(() => validateMetaAuthorizationUrl(url)).toThrow(/security validation/);
  });

  it("requires the exact popup source, origin, type and nonce", () => {
    const popup = {} as Window;
    const event = { origin: "https://socialos.test", source: popup, data: { type: "socialos:meta-connected", channelNonce: "nonce" } };
    expect(isTrustedMetaPopupMessage(event, "https://socialos.test", popup, "nonce")).toBe(true);
    expect(isTrustedMetaPopupMessage({ ...event, source: {} as Window }, "https://socialos.test", popup, "nonce")).toBe(false);
    expect(isTrustedMetaPopupMessage({ ...event, origin: "https://evil.test" }, "https://socialos.test", popup, "nonce")).toBe(false);
  });

  it("offers continuation only when a popup closes before its callback", () => {
    expect(shouldOfferPopupContinuation(true, "pending-nonce")).toBe(true);
    expect(shouldOfferPopupContinuation(true, null)).toBe(false);
    expect(shouldOfferPopupContinuation(false, "pending-nonce")).toBe(false);
  });

  it("completes once through BroadcastChannel when postMessage is not received", () => {
    let completed = 0;
    const receive = createMetaCompletionGuard("expected", () => completed += 1);
    expect(receive({ type: META_OAUTH_COMPLETION_TYPE, channelNonce: "wrong" })).toBe(false);
    expect(receive({ type: META_OAUTH_COMPLETION_TYPE, channelNonce: "expected" })).toBe(true);
    expect(receive({ type: META_OAUTH_COMPLETION_TYPE, channelNonce: "expected" })).toBe(false);
    expect(completed).toBe(1);
  });

  it.each([true, false])("broadcasts completion with opener available=%s", (hasOpener) => {
    const actions: string[] = [];
    const result = completeMetaSelection({
      channelNonce: "nonce",
      isPopup: true,
      hasOpener,
      postToOpener: () => actions.push("postMessage"),
      broadcast: () => actions.push("broadcast"),
      closePopup: () => actions.push("close"),
      navigate: () => actions.push("navigate"),
    });
    expect(result).toBe("popup");
    expect(actions).toEqual(hasOpener
      ? ["postMessage", "broadcast", "close"]
      : ["broadcast", "close"]);
  });

  it("navigates only when authorization used a full-page redirect", () => {
    const actions: string[] = [];
    expect(completeMetaSelection({
      channelNonce: "nonce",
      isPopup: false,
      hasOpener: false,
      postToOpener: () => actions.push("postMessage"),
      broadcast: () => actions.push("broadcast"),
      closePopup: () => actions.push("close"),
      navigate: () => actions.push("navigate"),
    })).toBe("redirect");
    expect(actions).toEqual(["broadcast", "navigate"]);
  });
});
