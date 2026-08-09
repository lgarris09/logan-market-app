// Small, dependency-free "time ago" formatter for the Opportunity Card's
// LAST UPDATED metadata readout -- reads only `delivered_at` (ISO8601,
// already public per the data contract), never a fabricated freshness/
// trend metric.
export function relativeTimeFrom(isoTimestamp: string, now: number = Date.now()): string {
  const then = new Date(isoTimestamp).getTime();
  if (Number.isNaN(then)) return "—";

  const diffMs = Math.max(0, now - then);
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  return `${days}d ago`;
}
