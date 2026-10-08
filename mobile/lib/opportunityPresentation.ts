// Beta 1 presentation helpers shared by every surface that shows an
// opportunity (feed, detail, notification dropdown, feedback context), so
// no two surfaces can describe the same opportunity differently.
//
// Pure presentation of fields the backend already decided. Nothing here
// scores, ranks, or infers anything, and nothing here invents content: when
// the backend has nothing real to say for a section, the helper returns null
// and the section is omitted.
import type { DeliveredItem, FeedItem, LifecycleState, TrajectoryState } from "../types/loganFeed";

/**
 * The condition-based evidence label (ADR-083): "Strong evidence",
 * "Supported evidence", "Limited evidence" or "Conflicting evidence". It
 * says how well-supported the observation is -- never a probability, a
 * recommendation, the size of the event, or its relevance to the user.
 *
 * Null when the backend sent no evidence strength. The older score-based
 * label is deliberately not used as a fallback.
 */
export function evidenceLabelFor(delivered: Pick<DeliveredItem, "evidence_label">): string | null {
  return delivered.evidence_label?.trim() || null;
}

// The limiting and critical conditions worth telling a user about, in the
// backend's own condition vocabulary
// (logan_core/conclusion_confidence/evidence_strength.py). Conditions that
// were simply met are not listed here; "single_origin" is stated because it
// is the reason a Supported label is not Strong.
const CONDITION_TEXT: Record<string, string> = {
  single_origin: "One source supports this; nothing independent confirms it yet.",
  details_incomplete: "Some expected details of the event are missing.",
  elevated_manipulation_risk: "The source pattern carries some manipulation risk.",
  freshness_within_grace:
    "STRATUS has not been able to refresh this recently. It may be out of date.",
  freshness_unconfirmed: "STRATUS cannot currently confirm how recent this is.",
  contradicting_evidence: "Contradicting evidence is on record.",
  high_manipulation_risk: "The source pattern carries high manipulation risk.",
};

/** The limiting factors behind the evidence label, as sentences, in the
 * order the backend listed them. Empty when there are none to state. */
export function evidenceLimitationsFor(
  delivered: Pick<DeliveredItem, "evidence_conditions">
): string[] {
  return (delivered.evidence_conditions ?? [])
    .map((code) => CONDITION_TEXT[code])
    .filter((text): text is string => !!text);
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
 * the backend found a personal basis for it, otherwise null -- the panel is
 * then omitted rather than filled with a sentence saying nothing connects.
 */
export function stratusTakeFor(item: Pick<FeedItem, "delivered_item">): string | null {
  const text = item.delivered_item.why_it_matters_to_me?.trim();
  if (!text) return null;
  const relevance = item.delivered_item.personal_relevance_result;
  if (relevance && relevance.basis === "none") return null;
  return text;
}

/**
 * WHAT CHANGED is the delta, not the event. The headline already states the
 * event, and the backend's `what_happened` is the same sentence, so it is
 * never repeated here. The delta is the lifecycle tracker's own reason for
 * the current state ("New signal appeared...", "No new evidence since the
 * original signal..."). Null when lifecycle tracking is not active and there
 * is nothing but the headline to say.
 */
export function whatChangedFor(
  item: Pick<FeedItem, "lifecycle_reason" | "delivered_item">
): string | null {
  const headline = item.delivered_item.headline.trim();
  const reason = item.lifecycle_reason?.trim();
  if (reason && reason !== headline) return reason.replace(/\s--\s/g, ": ");
  const happened = item.delivered_item.what_happened?.trim();
  if (happened && happened !== headline && !headline.startsWith(happened.slice(0, 110))) {
    return happened;
  }
  return null;
}

function ageText(hours: number | null | undefined): string | null {
  if (hours == null || !Number.isFinite(hours) || hours < 0) return null;
  if (hours < 1) return "within the last hour";
  if (hours < 48) {
    const h = Math.round(hours);
    return `${h} hour${h === 1 ? "" : "s"} ago`;
  }
  const d = Math.round(hours / 24);
  return `${d} days ago`;
}

const LIFECYCLE_NOW: Record<LifecycleState, string> = {
  new: "This is new.",
  developing: "The evidence is still developing.",
  high_attention: "This is active.",
  monitoring: "Nothing has changed that needs attention; STRATUS is still monitoring.",
  cooling: "There has been no new evidence since, so this is cooling.",
  stale: "There has been no new evidence for some time. This is stale.",
  expired: "This has expired.",
};

/**
 * WHY IT MATTERS NOW is about timing: when STRATUS first detected this and
 * where it is in its lifecycle. It never explains itself in terms of how or
 * whether a notification was sent. Null when lifecycle tracking is not
 * active for the item.
 */
export function whyNowFor(
  item: Pick<FeedItem, "lifecycle_state" | "thesis_age_hours">
): string | null {
  if (item.lifecycle_state == null) return null;
  const state = LIFECYCLE_NOW[item.lifecycle_state];
  if (!state) return null;
  const age = ageText(item.thesis_age_hours);
  return age ? `First detected ${age}. ${state}` : state;
}

const FAMILY_NAME: Record<string, string> = {
  earnings: "Earnings result",
  // ADR-084: SEC-filing catalysts. A results filing says results were
  // reported; it makes no comparison to consensus.
  earnings_result: "Results reported",
  company_event: "Company filing",
  analyst_grade: "Analyst action",
  price: "Price move",
};

/**
 * The signal families that qualified for this opportunity, when there is
 * more than one. Several families are several kinds of evidence about the
 * same company; they are not independent confirmation of each other and
 * are never described as corroboration. Null for a single family.
 */
export function supportingSignalsFor(item: Pick<FeedItem, "signal_families">): string[] | null {
  const names = (item.signal_families ?? [])
    .map((family) => FAMILY_NAME[family])
    .filter((name): name is string => !!name);
  return names.length > 1 ? names : null;
}
