// V2.3C Block P: a compile-time contract check as much as a runtime one --
// if backend/app/logan_feed.py's FeedItem ever adds/renames/removes a
// field, the object literal below stops satisfying the FeedItem type and
// this file fails to typecheck (tsc --noEmit / this test file's own
// import), catching drift immediately rather than silently. No shared-
// schema codegen exists in this project; this is the manual guard.
import { EvidenceSnapshot, FeedItem, SinceLastLookedSummary } from "../loganFeed";

const fullEvidence: EvidenceSnapshot = {
  schema_version: "1.0",
  entity_id: "NVDA",
  price: 190.5,
  trigger_price: 180.0,
  price_change_since_trigger_pct: 5.8,
  price_change_since_last_revision_pct: 1.2,
  market_change_pct: 0.4,
  relative_to_market_pct: 1.6,
  sector: "Technology",
  sector_change_pct: 0.9,
  relative_to_sector_pct: 0.7,
  volume: 45000000,
  average_volume: 40000000,
  volume_ratio: 1.125,
  beta: 1.7,
  beta_normalized_move_pct: 2.4,
  evaluated_at: "2026-08-29T00:00:00Z",
};

const fullyPopulatedItem: FeedItem = {
  event_id: "evt-1",
  entity_id: "NVDA",
  display_name: "NVIDIA",
  category: "stocks",
  ticker: "NVDA",
  domain: "stocks",
  delivered_item: {
    event_id: "evt-1",
    surface: "feed_card",
    headline: "NVIDIA beat earnings",
    what_happened: "NVDA reported EPS of 2.22 vs. consensus 2.09.",
    why_it_matters: "A real, notification-worthy beat.",
    why_it_matters_to_me: "You hold NVDA.",
    why_now: "Reported this quarter.",
    confidence_label: "High",
    confidence_score: 0.72,
    connected_items: [],
    required_disclaimers: [],
    delivered_at: "2026-08-29T00:00:00Z",
  },
  rank: 1,
  confidence_score: 0.72,
  confidence_label: "High",
  connected_event_ids: [],
  is_new_for_user: true,
  signal_type: "earnings_signal",
  lifecycle_state: "monitoring",
  is_updated: true,
  meaningful_change_type: "confidence_increased",
  lifecycle_reason: "Confidence strengthened.",
  last_meaningful_change_at: "2026-08-29T00:00:00Z",
  thesis_age_hours: 12.5,
  opportunity_revision: 6,
  user_sync_status: "UPDATED_SINCE_SEEN",
  trajectory: "STRENGTHENING",
  previous_trajectory: "STEADY",
  trajectory_reason: "Relative performance improved.",
  evidence: fullEvidence,
  since_last_looked: {
    schema_version: "1.0",
    entity_id: "NVDA",
    user_id: "user-1",
    status: "material_change",
    change_type: "confidence_increased",
    detail: "Confidence strengthened from 0.62 to 0.72.",
    evaluated_at: "2026-08-29T00:00:00Z",
  } satisfies SinceLastLookedSummary,
  is_watched: true,
};

// The inert-default shape every pre-V2.3C caller/fixture gets when
// lifecycle tracking isn't active for an entity (demo mode, no live
// tickers) -- absence means "not available," never an error.
const inertItem: FeedItem = {
  ...fullyPopulatedItem,
  lifecycle_state: null,
  is_updated: false,
  meaningful_change_type: null,
  lifecycle_reason: null,
  last_meaningful_change_at: null,
  thesis_age_hours: null,
  opportunity_revision: null,
  user_sync_status: null,
  trajectory: "STEADY",
  previous_trajectory: "STEADY",
  trajectory_reason: null,
  evidence: null,
  since_last_looked: null,
  is_watched: false,
};

// The "first_view" shape: lifecycle tracking is active, but this user has
// never opened this opportunity before -- change_type/detail stay null, no
// "since you last looked" language should ever be derived from this.
const firstViewItem: FeedItem = {
  ...fullyPopulatedItem,
  since_last_looked: {
    schema_version: "1.0",
    entity_id: "NVDA",
    user_id: "user-1",
    status: "first_view",
    change_type: null,
    detail: null,
    evaluated_at: "2026-08-29T00:00:00Z",
  } satisfies SinceLastLookedSummary,
};

describe("FeedItem/EvidenceSnapshot contract", () => {
  it("accepts a fully-populated V2/V2.1/V2.2 item", () => {
    expect(fullyPopulatedItem.lifecycle_state).toBe("monitoring");
    expect(fullyPopulatedItem.evidence?.relative_to_market_pct).toBe(1.6);
  });

  it("accepts the inert-default shape (lifecycle tracking not active)", () => {
    expect(inertItem.lifecycle_state).toBeNull();
    expect(inertItem.trajectory).toBe("STEADY");
    expect(inertItem.evidence).toBeNull();
    expect(inertItem.since_last_looked).toBeNull();
    expect(inertItem.is_watched).toBe(false);
  });

  it("accepts is_watched independent of lifecycle tracking", () => {
    expect(fullyPopulatedItem.is_watched).toBe(true);
    expect(inertItem.is_watched).toBe(false);
  });

  it("accepts a material_change since_last_looked summary", () => {
    expect(fullyPopulatedItem.since_last_looked?.status).toBe("material_change");
    expect(fullyPopulatedItem.since_last_looked?.change_type).toBe(
      "confidence_increased"
    );
    expect(fullyPopulatedItem.since_last_looked?.detail).toBeTruthy();
  });

  it("accepts a first_view since_last_looked summary with no change language", () => {
    expect(firstViewItem.since_last_looked?.status).toBe("first_view");
    expect(firstViewItem.since_last_looked?.change_type).toBeNull();
    expect(firstViewItem.since_last_looked?.detail).toBeNull();
  });
});
