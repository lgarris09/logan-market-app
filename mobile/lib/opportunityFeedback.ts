// ADR-082 -- opportunity-linked beta feedback.
//
// A report is an observed fact about one opportunity as the user saw it.
// It is sent through the existing telemetry path and changes nothing: not
// the opportunity, not its evidence, not Watch, not what STRATUS shows next.
import Constants from "expo-constants";

import type { FeedItem } from "../types/loganFeed";
import { describeTrajectory, evidenceLabelFor } from "./opportunityPresentation";
import {
  OpportunityFeedbackReason,
  submitTelemetryEvent,
  TelemetryEventInput,
  TelemetrySourceSurface,
} from "./telemetry";

export const FEEDBACK_NOTE_MAX_LENGTH = 500;

// The five governed options, in display order. Labels are fixed product
// copy; codes mirror backend/app/telemetry_models.py.
export const FEEDBACK_OPTIONS: readonly {
  reason: OpportunityFeedbackReason;
  label: string;
}[] = [
  { reason: "seems_wrong", label: "This seems wrong" },
  { reason: "stale", label: "This is stale" },
  { reason: "not_useful", label: "This is not useful to me" },
  { reason: "unclear_why", label: "I do not understand why I got this" },
  { reason: "expected_else", label: "I expected something else" },
];

function appBuild(): string | undefined {
  const version = Constants.expoConfig?.version;
  const build = Constants.nativeBuildVersion;
  if (!version && !build) return undefined;
  return [version, build ? `(${build})` : null].filter(Boolean).join(" ").slice(0, 32);
}

/**
 * Builds the telemetry event for one report. Pure: everything it records is
 * read from the item exactly as it was displayed. Returns null when the
 * item has no revision -- a report that cannot be tied to a revision cannot
 * be investigated, and the backend refuses it.
 */
export function buildFeedbackEvent(
  item: FeedItem,
  reason: OpportunityFeedbackReason,
  note: string,
  sourceSurface: TelemetrySourceSurface = "feed_card"
): TelemetryEventInput | null {
  if (item.opportunity_revision == null) return null;
  const trimmed = note.trim().slice(0, FEEDBACK_NOTE_MAX_LENGTH);
  return {
    eventName: "opportunity_feedback_submitted",
    opportunityId: item.event_id,
    opportunityRevision: item.opportunity_revision,
    sourceSurface,
    context: {
      entityId: item.entity_id,
      feedbackReason: reason,
      feedbackNote: trimmed || undefined,
      displayedHeadline: item.delivered_item.headline.slice(0, 300),
      displayedEvidenceLabel: evidenceLabelFor(item),
      displayedTrajectory: describeTrajectory(item)?.label,
      displayedFreshnessState: item.freshness_state ?? undefined,
      displayedAt: item.delivered_item.delivered_at,
      appBuild: appBuild(),
    },
  };
}

export type FeedbackSubmitResult = "sent" | "failed" | "unavailable";

/** Sends one report. "unavailable" means this item cannot be reported
 * against (no revision); "failed" means the request did not get through
 * and the user should be told so. */
export async function submitOpportunityFeedback(
  item: FeedItem,
  reason: OpportunityFeedbackReason,
  note: string,
  sourceSurface?: TelemetrySourceSurface
): Promise<FeedbackSubmitResult> {
  const event = buildFeedbackEvent(item, reason, note, sourceSurface);
  if (event === null) return "unavailable";
  return (await submitTelemetryEvent(event)) ? "sent" : "failed";
}
