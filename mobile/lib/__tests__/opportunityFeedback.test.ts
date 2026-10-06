import { fetchJson } from "../apiClient";
import {
  buildFeedbackEvent,
  FEEDBACK_NOTE_MAX_LENGTH,
  FEEDBACK_OPTIONS,
  submitOpportunityFeedback,
} from "../opportunityFeedback";
import {
  describeTrajectory,
  evidenceLabelFor,
  evidenceLimitationsFor,
  stratusTakeFor,
  supportingSignalsFor,
  whatChangedFor,
  whyNowFor,
} from "../opportunityPresentation";
import type { FeedItem } from "../../types/loganFeed";

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));
jest.mock("expo-crypto", () => ({ randomUUID: jest.fn(() => "generated-uuid") }));
jest.mock("expo-constants", () => ({
  __esModule: true,
  default: { expoConfig: { version: "1.2.3" }, nativeBuildVersion: "42" },
}));

const mockedFetchJson = fetchJson as jest.Mock;

function item(overrides: Partial<FeedItem> = {}): FeedItem {
  return {
    event_id: "evt-1",
    entity_id: "NVDA",
    display_name: "NVIDIA",
    category: "stocks",
    ticker: "NVDA",
    domain: "stocks",
    delivered_item: {
      headline: "NVIDIA: analyst upgrade",
      what_happened: "NVIDIA: analyst upgrade",
      why_it_matters: "generic",
      why_it_matters_to_me: "You watch NVIDIA.",
      why_now: "No immediate time pressure; surfaced for background awareness.",
      evidence_strength: "supported",
      evidence_label: "Supported evidence",
      evidence_conditions: ["qualified", "single_origin", "details_complete", "no_conflict"],
      delivered_at: "2026-10-05T21:00:00+00:00",
    } as FeedItem["delivered_item"],
    rank: 1,
    confidence_score: 0.6,
    confidence_label: "Moderate",
    connected_event_ids: [],
    is_new_for_user: false,
    signal_type: "analyst_change",
    lifecycle_state: "cooling",
    is_updated: false,
    meaningful_change_type: null,
    lifecycle_reason: "No new evidence since the original signal -- STRATUS is still monitoring.",
    last_meaningful_change_at: null,
    thesis_age_hours: 3,
    opportunity_revision: 4,
    user_sync_status: null,
    trajectory: "STRENGTHENING",
    previous_trajectory: "STEADY",
    trajectory_reason: "Relative performance improved by 1.4pp.",
    evidence: null,
    since_last_looked: null,
    is_watched: false,
    freshness_state: "FRESH",
    signal_families: ["analyst_grade"],
    ...overrides,
  };
}

describe("feedback options", () => {
  it("offers exactly the five governed reasons, in order", () => {
    expect(FEEDBACK_OPTIONS.map((o) => o.reason)).toEqual([
      "seems_wrong",
      "stale",
      "not_useful",
      "unclear_why",
      "expected_else",
    ]);
    expect(FEEDBACK_OPTIONS.map((o) => o.label)).toEqual([
      "This seems wrong",
      "This is stale",
      "This is not useful to me",
      "I do not understand why I got this",
      "I expected something else",
    ]);
  });
});

describe("buildFeedbackEvent", () => {
  it("preserves the opportunity, revision and what was displayed", () => {
    const event = buildFeedbackEvent(item(), "stale", "  shown as new  ");
    expect(event).not.toBeNull();
    expect(event).toMatchObject({
      eventName: "opportunity_feedback_submitted",
      opportunityId: "evt-1",
      opportunityRevision: 4,
      context: {
        entityId: "NVDA",
        feedbackReason: "stale",
        feedbackNote: "shown as new",
        displayedHeadline: "NVIDIA: analyst upgrade",
        displayedEvidenceLabel: "Supported evidence",
        displayedTrajectory: "Evidence strengthening",
        displayedFreshnessState: "FRESH",
        displayedAt: "2026-10-05T21:00:00+00:00",
        appBuild: "1.2.3 (42)",
      },
    });
  });

  it("omits an empty note and bounds a long one", () => {
    expect(buildFeedbackEvent(item(), "stale", "   ")?.context?.feedbackNote).toBeUndefined();
    const long = buildFeedbackEvent(item(), "stale", "x".repeat(900));
    expect(long?.context?.feedbackNote).toHaveLength(FEEDBACK_NOTE_MAX_LENGTH);
  });

  it("never sends a model version -- that is a server fact", () => {
    const event = buildFeedbackEvent(item(), "seems_wrong", "");
    expect(JSON.stringify(event)).not.toMatch(/model/i);
  });

  it("returns null when there is no revision to attribute the report to", () => {
    expect(buildFeedbackEvent(item({ opportunity_revision: null }), "stale", "")).toBeNull();
  });
});

describe("submitOpportunityFeedback", () => {
  beforeEach(() => jest.clearAllMocks());

  it("posts a snake_case body to the telemetry route and reports success", async () => {
    mockedFetchJson.mockResolvedValue({ status: "success", data: {} });
    await expect(submitOpportunityFeedback(item(), "unclear_why", "")).resolves.toBe("sent");

    const [path, options] = mockedFetchJson.mock.calls[0];
    expect(path).toBe("/v1/telemetry/events");
    const body = JSON.parse(options.body);
    expect(body.event_name).toBe("opportunity_feedback_submitted");
    expect(body.opportunity_id).toBe("evt-1");
    expect(body.opportunity_revision).toBe(4);
    expect(body.context.entity_id).toBe("NVDA");
    expect(body.context.feedback_reason).toBe("unclear_why");
    expect(body.context.displayed_evidence_label).toBe("Supported evidence");
    expect(body.context.model_version).toBeUndefined();
  });

  it("tells the caller when the report did not get through", async () => {
    mockedFetchJson.mockResolvedValue({ status: "error", error: "network" });
    await expect(submitOpportunityFeedback(item(), "stale", "")).resolves.toBe("failed");
  });

  it("sends nothing for an item that cannot be reported against", async () => {
    await expect(
      submitOpportunityFeedback(item({ opportunity_revision: null }), "stale", "")
    ).resolves.toBe("unavailable");
    expect(mockedFetchJson).not.toHaveBeenCalled();
  });
});

describe("presentation helpers", () => {
  it("shows the backend's condition-based label and never the old score label", () => {
    expect(evidenceLabelFor(item().delivered_item)).toBe("Supported evidence");
    const old = item();
    old.delivered_item = { ...old.delivered_item, evidence_label: null };
    expect(evidenceLabelFor(old.delivered_item)).toBeNull();
    for (const label of ["Strong", "Supported", "Limited", "Conflicting"]) {
      expect(evidenceLabelFor({ evidence_label: `${label} evidence` })).not.toMatch(/[0-9%]/);
    }
  });

  it("states the limiting factors behind the label, and only those", () => {
    expect(evidenceLimitationsFor(item().delivered_item)).toEqual([
      "One source supports this; nothing independent confirms it yet.",
    ]);
    expect(
      evidenceLimitationsFor({
        evidence_conditions: ["qualified", "independent_corroboration", "freshness_established"],
      })
    ).toEqual([]);
    expect(evidenceLimitationsFor({ evidence_conditions: ["freshness_unconfirmed"] })[0]).toMatch(
      /cannot currently confirm/
    );
    expect(evidenceLimitationsFor({})).toEqual([]);
  });

  it("describes trajectory as observed evidence, not a forecast", () => {
    for (const state of ["STRENGTHENING", "STEADY", "WEAKENING", "REVERSING"] as const) {
      const t = describeTrajectory(item({ trajectory: state }));
      expect(t?.label).toMatch(/^Evidence /);
      expect(t?.label).not.toMatch(/will|expect|likely|target|buy|sell|predict/i);
    }
  });

  it("reports no trajectory when lifecycle tracking is not active", () => {
    expect(describeTrajectory(item({ lifecycle_state: null }))).toBeNull();
  });

  it("shows STRATUS TAKE only when there is a personal basis", () => {
    expect(stratusTakeFor(item())).toBe("You watch NVIDIA.");
    const blank = item();
    blank.delivered_item = { ...blank.delivered_item, why_it_matters_to_me: "  " };
    expect(stratusTakeFor(blank)).toBeNull();
    const none = item();
    none.delivered_item = {
      ...none.delivered_item,
      why_it_matters_to_me:
        "Nothing in your current holdings or interests is directly connected to this yet.",
      personal_relevance_result: {
        value: 0,
        state: "unknown",
        basis: "none",
        is_watched: false,
        evidence_count: 0,
        explicit: false,
        strongest_signals: [],
        not_contributing: [],
        explanation: "",
      },
    };
    expect(stratusTakeFor(none)).toBeNull();
  });

  it("WHAT CHANGED is the delta and never repeats the headline", () => {
    expect(whatChangedFor(item())).toBe(
      "No new evidence since the original signal: STRATUS is still monitoring."
    );
    expect(whatChangedFor(item({ lifecycle_reason: null }))).toBeNull();
    expect(whatChangedFor(item({ lifecycle_reason: "NVIDIA: analyst upgrade" }))).toBeNull();
  });

  it("WHY NOW is lifecycle timing and never notification mechanics", () => {
    const text = whyNowFor(item());
    expect(text).toBe(
      "First detected 3 hours ago. There has been no new evidence since, so this is cooling."
    );
    for (const state of [
      "new",
      "developing",
      "high_attention",
      "monitoring",
      "cooling",
      "stale",
      "expired",
    ] as const) {
      const t = whyNowFor(item({ lifecycle_state: state, thesis_age_hours: 80 }));
      expect(t).toMatch(/^First detected 3 days ago\. /);
      expect(t).not.toMatch(/interruption|notif|alert|push|check-in|flag/i);
      expect(t).not.toMatch(/will|expect|likely|predict|buy|sell/i);
    }
    expect(whyNowFor(item({ lifecycle_state: null }))).toBeNull();
    expect(whyNowFor(item({ thesis_age_hours: null }))).toBe(
      "There has been no new evidence since, so this is cooling."
    );
  });

  it("lists supporting signals only when more than one family qualified", () => {
    expect(supportingSignalsFor(item())).toBeNull();
    expect(supportingSignalsFor(item({ signal_families: undefined }))).toBeNull();
    const names = supportingSignalsFor(item({ signal_families: ["analyst_grade", "price"] }));
    expect(names).toEqual(["Analyst action", "Price move"]);
    expect(names?.join(" ")).not.toMatch(/corroborat|confirm/i);
  });
});
