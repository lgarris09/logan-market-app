// Beta 1 presentation helpers shared by every surface that shows an
// opportunity (feed, detail, notification dropdown, feedback context), so
// no two surfaces can describe the same opportunity differently.
//
// Pure presentation of fields the backend already decided. Nothing here
// scores, ranks, or infers anything.
import type { FeedItem, TrajectoryState } from "../types/loganFeed";

/**
 * How well-evidenced the observation is -- never a probability and never a
 * percentage (ADR-077). The same wording on every surface.
 */
export function evidenceLabelFor(item: Pick<FeedItem, "confidence_label">): string {
  return `${item.confidence_label} evidence`;
}

export type TrajectoryPresentation = {
  /** Short, evidence-worded state, e.g. "Evidence strengthening". */
  label: string;
  /** The backend's own reason for that state, shown as-is. */
  reason: string | null;
  icon: string;
  tone: "up" | "down" | "flat" | "turn";
};

// Trajectory describes how the observed evidence has changed since STRATUS
// started tracking this opportunity. It says nothing about where a price
// is expected to go, and the wording below must never suggest it does.
const TRAJECTORY: Record<TrajectoryState, Omit<TrajectoryPresentation, "reason">> = {
  STRENGTHENING: {
    label: "Evidence strengthening",
    icon: "trending-up-outline",
    tone: "up",
  },
  STEADY: { label: "Evidence steady", icon: "remove-outline", tone: "flat" },
  WEAKENING: {
    label: "Evidence weakening",
    icon: "trending-down-outline",
    tone: "down",
  },
  REVERSING: {
    label: "Evidence reversing",
    icon: "swap-vertical-outline",
    tone: "turn",
  },
};

/**
 * Returns null when lifecycle tracking is not active for this item
 * (lifecycle_state is null): there is no observed trajectory to report, and
 * the default "STEADY" the contract carries in that case is a placeholder,
 * not a finding.
 */
export function describeTrajectory(
  item: Pick<FeedItem, "trajectory" | "trajectory_reason" | "lifecycle_state">
): TrajectoryPresentation | null {
  if (item.lifecycle_state == null) return null;
  const base = TRAJECTORY[item.trajectory];
  if (!base) return null;
  return { ...base, reason: item.trajectory_reason?.trim() || null };
}

/**
 * STRATUS TAKE is personal relevance only. Returns the personal text when
 * the backend supplied one, otherwise null -- the panel is then omitted
 * rather than filled with a restatement of what happened.
 */
export function stratusTakeFor(item: Pick<FeedItem, "delivered_item">): string | null {
  return item.delivered_item.why_it_matters_to_me?.trim() || null;
}

/**
 * What the user is told when STRATUS cannot vouch for how current the data
 * is. Null when there is nothing to qualify.
 */
export function freshnessNoticeFor(freshnessState: string | null | undefined): string | null {
  switch (freshnessState) {
    case "STALE_WITHIN_GRACE":
      return "STRATUS has not been able to refresh this recently. It may be out of date.";
    case "UNAVAILABLE":
      return "STRATUS cannot currently confirm how recent this is.";
    default:
      return null;
  }
}
