import { describe, expect, it } from "vitest";

import type { PublicationAttempt } from "./api";
import { groupPublicationAttempts } from "./publication-attempts";

function event(
  id: string,
  attemptNumber: number,
  status: PublicationAttempt["status"],
  createdAt: string,
): PublicationAttempt {
  return {
    id,
    publication_id: "8c086ab8-eaac-4d87-a6fb-8f3268a133e7",
    attempt_number: attemptNumber,
    status,
    provider: "local-dev",
    request_id: null,
    error_code: null,
    error_message: status.includes("failed")
      ? "Temporary local provider failure"
      : null,
    external_publication_id:
      status === "succeeded" ? "local-publication-1" : null,
    created_at: createdAt,
  };
}

describe("groupPublicationAttempts", () => {
  it("counts a successful started/succeeded sequence as one logical attempt", () => {
    const groups = groupPublicationAttempts([
      event(
        "d7bd244e-fc21-43cf-9c94-09838336cd98",
        1,
        "succeeded",
        "2026-07-31T10:01:00Z",
      ),
      event(
        "0315bb80-703c-4616-b4cb-da41495335db",
        1,
        "started",
        "2026-07-31T10:00:00Z",
      ),
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0]?.events.map(({ status }) => status)).toEqual([
      "started",
      "succeeded",
    ]);
  });

  it("groups a failed attempt and its retry into two logical attempts", () => {
    const groups = groupPublicationAttempts([
      event(
        "b128d42a-cfe2-4318-954d-c66ec574ecdf",
        2,
        "succeeded",
        "2026-07-31T10:04:00Z",
      ),
      event(
        "55c1cd09-35df-445a-9274-8a343127f1ab",
        1,
        "failed_retryable",
        "2026-07-31T10:02:00Z",
      ),
      event(
        "2b17694a-c284-470f-b4c4-f8b9e3796285",
        2,
        "started",
        "2026-07-31T10:03:00Z",
      ),
      event(
        "cfb546c5-972b-418d-8aa7-61110a56ee11",
        1,
        "started",
        "2026-07-31T10:01:00Z",
      ),
    ]);

    expect(groups).toHaveLength(2);
    expect(groups.map(({ attemptNumber }) => attemptNumber)).toEqual([1, 2]);
    expect(groups[0]?.events.map(({ status }) => status)).toEqual([
      "started",
      "failed_retryable",
    ]);
    expect(groups[1]?.events.map(({ status }) => status)).toEqual([
      "started",
      "succeeded",
    ]);
  });
});
