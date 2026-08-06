"use server";

import { revalidatePath } from "next/cache";

import {
  authorizeMeta,
  disconnectMeta,
  type MetaConnectionIntent,
  selectMetaCandidate,
  validateMeta,
} from "@/lib/api";

export async function startMetaAuthorization(
  workspaceId: string,
  intent: MetaConnectionIntent,
  connectionId?: string,
) {
  return authorizeMeta(workspaceId, intent, connectionId);
}

export async function selectMetaCandidateAction(sessionId: string, candidateId: string) {
  return selectMetaCandidate(sessionId, candidateId);
}

export async function disconnectMetaAction(connectionId: string) {
  await disconnectMeta(connectionId);
  revalidatePath("/integrations");
}

export async function validateMetaAction(connectionId: string) {
  const valid = await validateMeta(connectionId);
  revalidatePath("/integrations");
  return valid;
}
