// Mirrors backend/app/logan_feed.py's DemoFeedResponse/FeedItem and
// backend/app/opportunities.py's OpportunitiesResponse.

// STRATUS Recommendation + Risk (Sprint 3.6 presentation foundation, section
// 9-14): the future premium "what should I consider doing about this" layer.
// No current backend response populates this -- logan_core's DeliveredItem
// contract (docs/specs/.../07_DATA_CONTRACTS.md) has no recommendation/risk
// concept yet -- so it's optional and, in the live app today, always
// undefined. This is the honest contract boundary the mobile UI renders
// against: components/RecommendationPanel.tsx shows a locked teaser
// whenever it's absent rather than fabricating an action, risk, or
// condition. `risk` is deliberately a separate axis from
// confidence_score/confidence_label above -- see RecommendationPanel.tsx's
// own comment for why the two must never collapse into one presented value.
export type RecommendationRisk = "low" | "moderate" | "high" | "speculative";

export type Recommendation = {
  action: string;
  risk: RecommendationRisk;
  whatWouldChangeThis?: string;
};

export type DeliveredItem = {
  event_id: string;
  surface: "wheel" | "feed_card" | "alert" | "digest" | "background";
  headline: string;
  what_happened: string;
  why_it_matters: string;
  why_it_matters_to_me: string;
  why_now: string;
  confidence_label: "High" | "Moderate" | "Low" | "Speculative";
  confidence_score: number;
  connected_items: string[];
  required_disclaimers: string[];
  delivered_at: string;
  recommendation?: Recommendation;
};

export type FeedItem = {
  event_id: string;
  entity_id: string;
  display_name: string;
  category: string;
  ticker: string | null;
  domain: string;
  delivered_item: DeliveredItem;
  // 1-indexed position in this response's already-sorted order (1 = most
  // important). The backend's internal ranking score is never exposed here
  // (ADR-029) -- `rank` is the correct public-facing ordering signal.
  rank: number;
  confidence_score: number;
  confidence_label: "High" | "Moderate" | "Low" | "Speculative";
  connected_event_ids: string[];
  // Whether this event_id is unread for the current user, computed
  // server-side (PrioritizationEngine.mark_reviewed/is_new_for_user) --
  // deliberately not the same concept as event identity/dedup (a
  // re-observation of the same underlying opportunity keeps this the same
  // value it already had, it doesn't reset to true). False on this user's
  // very first-ever response, and after POSTing to
  // /v1/notifications/review. In-memory on the backend, process-lifetime
  // only -- resets on a backend restart. Replaces the earlier client-side
  // event_id-diffing approach, which couldn't distinguish "the same
  // opportunity observed again" from "a genuinely new one" because the old
  // backend handed out a fresh random event_id on every single request.
  is_new_for_user: boolean;
  // The real Normalization-layer signal_type behind this opportunity's
  // primary signal (e.g. "earnings_signal", "volatility_spike") -- real
  // data, not a hand-authored short label (no such field exists anywhere
  // in the pipeline). Used as the honest source for the Attention Field
  // vessel's small reason tag -- see lib/signalType.ts.
  signal_type: string;
};

export type DemoFeedResponse = {
  items: FeedItem[];
  generated_at: string;
};

// /v1/opportunities' response shape (V3.1.4 BATCH-4) -- same FeedItem shape as the
// deprecated /v1/demo/feed, plus schema_version metadata.
export type OpportunitiesResponse = {
  schema_version: string;
  items: FeedItem[];
  generated_at: string;
};
