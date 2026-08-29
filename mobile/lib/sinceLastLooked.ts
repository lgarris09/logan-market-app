// V2.3D ("Since You Last Looked") -- pure presentation mapping over the
// backend-authoritative SinceLastLookedSummary. This file owns NO delta
// semantics of its own: `status`/`change_type`/`detail` are computed
// server-side (opportunity_lifecycle/sync.py's compute_since_last_looked)
// and handed through untouched. What this file owns is purely cosmetic --
// which section label/icon/tone to render for a given status/change_type --
// mirroring how components/OpportunityCard.tsx's own `surfaceLabels` is a
// static lookup over a backend-provided enum, never a re-derivation of it.
import { MeaningfulChangeType, SinceLastLookedSummary } from "../types/loganFeed";

export type SinceLastLookedTone = "material" | "quiet" | "degraded";

export type SinceLastLookedPresentation = {
  tone: SinceLastLookedTone;
  label: string;
  icon: string;
  text: string;
};

// One icon per MeaningfulChangeType that can actually appear on a
// material_change summary -- deliberately a Partial so an unrecognized
// (e.g. future) change_type falls back to DEFAULT_MATERIAL_ICON below
// rather than a missing-key crash.
const CHANGE_TYPE_ICON: Partial<Record<MeaningfulChangeType, string>> = {
  trajectory_strengthening: "trending-up-outline",
  trajectory_reaccelerated: "trending-up-outline",
  trajectory_weakening: "trending-down-outline",
  trajectory_reversing: "swap-vertical-outline",
  confidence_increased: "trending-up-outline",
  confidence_decreased: "trending-down-outline",
  new_signal_appeared: "flash-outline",
  convergence_formed: "git-merge-outline",
  reactivated: "refresh-outline",
  new_opportunity: "sparkles-outline",
  aged_to_cooling: "snow-outline",
  aged_to_stale: "hourglass-outline",
  aged_to_expired: "close-circle-outline",
};

const DEFAULT_MATERIAL_ICON = "swap-vertical-outline";

/**
 * Returns null for "first_view" (and for a null/absent summary, i.e.
 * lifecycle tracking not active for this entity) -- the caller must render
 * nothing in either case, per the explicit "no fake since-you-last-looked
 * language" product requirement. Every other status returns a ready-to-
 * render presentation; `text` always falls back to a generic (never
 * fabricated-as-data, just a defensive placeholder) sentence if the backend
 * ever sends a null `detail` outside of first_view, which the contract
 * doesn't currently allow but this file doesn't assume.
 */
export function describeSinceLastLooked(
  summary: SinceLastLookedSummary | null | undefined
): SinceLastLookedPresentation | null {
  if (!summary) return null;

  switch (summary.status) {
    case "first_view":
      return null;
    case "material_change":
      return {
        tone: "material",
        label: "SINCE YOU LAST LOOKED",
        icon:
          (summary.change_type && CHANGE_TYPE_ICON[summary.change_type]) ||
          DEFAULT_MATERIAL_ICON,
        text: summary.detail ?? "Something changed since your last look.",
      };
    case "no_material_change":
      return {
        tone: "quiet",
        label: "STILL MONITORING",
        icon: "eye-outline",
        text: summary.detail ?? "No major change since your last look.",
      };
    case "degraded":
      return {
        tone: "degraded",
        label: "LIVE DATA UNAVAILABLE",
        icon: "cloud-offline-outline",
        text:
          summary.detail ??
          "STRATUS couldn't confirm the latest data this check.",
      };
    default:
      return null;
  }
}
