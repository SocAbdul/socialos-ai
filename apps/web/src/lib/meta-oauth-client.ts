export const META_OAUTH_BROADCAST_CHANNEL = "socialos-meta-oauth";
export const META_OAUTH_POPUP_NAME = "socialos-meta";
export const META_OAUTH_COMPLETION_TYPE = "socialos:meta-connected";

export type MetaCompletionMessage = {
  type: typeof META_OAUTH_COMPLETION_TYPE;
  channelNonce: string;
};

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
    data?.type === META_OAUTH_COMPLETION_TYPE &&
    data.channelNonce === channelNonce,
  );
}

export function isTrustedMetaCompletionMessage(
  data: unknown,
  channelNonce: string | null,
): data is MetaCompletionMessage {
  if (!channelNonce || !data || typeof data !== "object") return false;
  const message = data as { type?: unknown; channelNonce?: unknown };
  return message.type === META_OAUTH_COMPLETION_TYPE && message.channelNonce === channelNonce;
}

export function createMetaCompletionGuard(
  channelNonce: string,
  complete: () => void,
): (data: unknown) => boolean {
  let completed = false;
  return (data: unknown) => {
    if (completed || !isTrustedMetaCompletionMessage(data, channelNonce)) return false;
    completed = true;
    complete();
    return true;
  };
}

export function completeMetaSelection(options: {
  channelNonce: string;
  isPopup: boolean;
  hasOpener: boolean;
  postToOpener: (message: MetaCompletionMessage) => void;
  broadcast: (message: MetaCompletionMessage) => void;
  closePopup: () => void;
  navigate: () => void;
}): "popup" | "redirect" {
  const message: MetaCompletionMessage = {
    type: META_OAUTH_COMPLETION_TYPE,
    channelNonce: options.channelNonce,
  };
  if (options.hasOpener) options.postToOpener(message);
  options.broadcast(message);
  if (options.isPopup) {
    options.closePopup();
    return "popup";
  }
  options.navigate();
  return "redirect";
}

export function shouldOfferPopupContinuation(
  popupClosed: boolean,
  pendingChannelNonce: string | null,
): boolean {
  return popupClosed && pendingChannelNonce !== null;
}
