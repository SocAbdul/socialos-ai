export function validateMetaAuthorizationUrl(value: string): string {
  const url = new URL(value);
  if (
    url.protocol !== "https:" ||
    url.hostname !== "www.facebook.com" ||
    url.username ||
    url.password ||
    !url.searchParams.get("config_id") ||
    url.searchParams.get("response_type") !== "code" ||
    url.searchParams.has("scope")
  ) {
    throw new Error("The Meta authorization URL failed security validation.");
  }
  return url.toString();
}

export function isTrustedMetaPopupMessage(
  event: Pick<MessageEvent, "origin" | "source" | "data">,
  expectedOrigin: string,
  popup: Window | null,
  channelNonce: string | null,
): boolean {
  const data = event.data as { type?: string; channelNonce?: string } | null;
  return Boolean(
    popup &&
    channelNonce &&
    event.origin === expectedOrigin &&
    event.source === popup &&
    data?.type === "socialos:meta-connected" &&
    data.channelNonce === channelNonce,
  );
}

export function shouldOfferPopupContinuation(
  popupClosed: boolean,
  pendingChannelNonce: string | null,
): boolean {
  return popupClosed && pendingChannelNonce !== null;
}
