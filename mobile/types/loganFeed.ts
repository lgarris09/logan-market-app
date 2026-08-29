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

// V2.3C Block P: mirrors logan_core.contracts.lifecycle's own Literal
// definitions exactly (Python is authoritative; no shared-schema codegen
// exists in this project, so these are kept in sync by hand). "none" is a
// real, expected MeaningfulChangeType value -- most polls produce no
// meaningful change at all.
export type LifecycleState =
  | "new"
  | "developing"
  | "high_attention"
  | "monitoring"
  | "cooling"
  | "stale"
  | "expired";

export type MeaningfulChangeType =
  | "none"
  | "new_opportunity"
  | "confidence_increased"
  | "confidence_decreased"
  | "new_signal_appeared"
  | "convergence_formed"
  | "aged_to_cooling"
  | "aged_to_stale"
  | "aged_to_expired"
  | "reactivated"
  | "personal_relevance_increased"
  | "personal_relevance_decreased"
  | "trajectory_strengthening"
  | "trajectory_weakening"
  | "trajectory_reversing"
  | "trajectory_reaccelerated";

export type TrajectoryState = "STRENGTHENING" | "STEADY" | "WEAKENING" | "REVERSING";

// Mirrors opportunity_lifecycle/sync.py's SyncStatus exactly.
export type UserSyncStatus =
  | "UP_TO_DATE"
  | "NEW_TO_USER"
  | "UPDATED_SINCE_SEEN"
  | "NOTIFIED_BUT_UNSEEN";

// V2.3D ("Since You Last Looked"). Mirrors opportunity_lifecycle/sync.py's
// SinceLastLookedStatus exactly. A deliberately stricter question than
// UserSyncStatus above -- keyed to last_opened_revision (a real card
// disclosure), never last_seen_revision (which advances on a mere
// impression). "first_view" means this user has never opened this
// opportunity before -- present the briefing normally, no "since you last
// looked" language of any kind.
export type SinceLastLookedStatus =
  | "first_view"
  | "material_change"
  | "no_material_change"
  | "degraded";

// Mirrors opportunity_lifecycle/sync.py's SinceLastLookedSummary exactly.
// change_type/detail are only ever populated for "material_change" --
// detail is the backend's own already-authored natural-language sentence
// (the same OpportunityRevision.reason logan_core's tracker.py produces
// elsewhere), never re-derived or re-worded on this side.
export type SinceLastLookedSummary = {
  schema_version: string;
  entity_id: string;
  user_id: string;
  status: SinceLastLookedStatus;
  change_type: MeaningfulChangeType | null;
  detail: string | null;
  evaluated_at: string;
};

// Mirrors logan_core.contracts.lifecycle.EvidenceSnapshot -- every field
// individually optional since a real provider may supply some (price)
// without others (sector, beta) depending on what's reachable that poll.
export type EvidenceSnapshot = {
  schema_version: string;
  entity_id: string;
  price: number | null;
  trigger_price: number | null;
  price_change_since_trigger_pct: number | null;
  price_change_since_last_revision_pct: number | null;
  market_change_pct: number | null;
  relative_to_market_pct: number | null;
  sector: string | null;
  sector_change_pct: number | null;
  relative_to_sector_pct: number | null;
  volume: number | null;
  average_volume: number | null;
  volume_ratio: number | null;
  beta: number | null;
  beta_normalized_move_pct: number | null;
  evaluated_at: string;
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

  // --- V2.3C Block P: Stock Opportunity Logic V2/V2.1/V2.2 fields --------
  // Mirrors backend/app/logan_feed.py's FeedItem exactly. All optional/
  // default-inert (null, false, "none", "STEADY") whenever lifecycle
  // tracking isn't active for this entity (demo mode, no live tickers
  // configured) -- absence means "not available for this item," never an
  // error. Added here as a type-only contract update (V2.3C Block P) --
  // no UI currently renders these; that remains a separate, deliberate
  // product decision, not something to wire silently as a side effect of
  // fixing this type gap.
  lifecycle_state: LifecycleState | null;
  is_updated: boolean;
  meaningful_change_type: MeaningfulChangeType | null;
  lifecycle_reason: string | null;
  last_meaningful_change_at: string | null;
  thesis_age_hours: number | null;
  opportunity_revision: number | null;
  user_sync_status: UserSyncStatus | null;
  trajectory: TrajectoryState;
  previous_trajectory: TrajectoryState;
  trajectory_reason: string | null;
  evidence: EvidenceSnapshot | null;

  // V2.3D ("Since You Last Looked"). null whenever lifecycle tracking isn't
  // active for this entity -- same additive discipline as every field
  // above. This is the single backend-authoritative answer to "what
  // changed since this user last looked" -- rendered as-is, never
  // re-derived from opportunity_revision/user_sync_status on this side.
  since_last_looked: SinceLastLookedSummary | null;
};

export type DemoFeedResponse = {
  items: FeedItem[];
  generated_at: string;
  // V2.3A.1 field reliability work: true iff at least one configured live
  // ticker's data was genuinely unreachable this poll (a real provider
  // outage), as opposed to "nothing currently qualifies" -- see
  // backend/app/logan_feed.py's DemoFeedResponse.provider_degraded. Optional
  // because older cached/mocked responses in tests may omit it.
  provider_degraded?: boolean;
};

// /v1/opportunities' response shape (V3.1.4 BATCH-4) -- same FeedItem shape as the
// deprecated /v1/demo/feed, plus schema_version metadata.
export type OpportunitiesResponse = {
  schema_version: string;
  items: FeedItem[];
  generated_at: string;
  // See DemoFeedResponse.provider_degraded above -- same field, same meaning.
  provider_degraded?: boolean;
};
