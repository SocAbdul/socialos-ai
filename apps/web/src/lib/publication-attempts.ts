import type { PublicationAttempt } from "@/lib/api";

export type PublicationAttemptGroup = {
  attemptNumber: number;
  events: PublicationAttempt[];
};

const eventOrder: Record<PublicationAttempt["status"], number> = {
  started: 0,
  succeeded: 1,
  failed_retryable: 1,
  failed_permanent: 1,
};

export function groupPublicationAttempts(
  attempts: PublicationAttempt[],
): PublicationAttemptGroup[] {
  const groups = new Map<number, PublicationAttempt[]>();

  for (const attempt of attempts) {
    const events = groups.get(attempt.attempt_number) ?? [];
    events.push(attempt);
    groups.set(attempt.attempt_number, events);
  }

  return [...groups.entries()]
    .sort(([left], [right]) => left - right)
    .map(([attemptNumber, events]) => ({
      attemptNumber,
      events: events.toSorted((left, right) => {
        const timestampDifference =
          new Date(left.created_at).getTime() -
          new Date(right.created_at).getTime();
        return (
          timestampDifference ||
          eventOrder[left.status] - eventOrder[right.status]
        );
      }),
    }));
}
