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
  freshnessNoticeFor,
  stratusTakeFor,
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
      what_happened: "NVIDIA: analyst change (upgraded)",
      why_it_matters: "generic",
      why_it_matters_to_me: "You watch NVIDIA.",
      delivered_at: "2026-10-05T21:00:00+00:00",
    } as FeedItem["delivered_item"],
    rank: 1,
    confidence_score: 0.6,
    confidence_label: "Moderate",
    connected_event_ids: [],
    is_new_for_user: false,
    signal_type: "analyst_change",
    lifecycle_state: "ACTIVE" as FeedItem["lifecycle_state"],
    is_updated: false,
    meaningful_change_type: null,
    lifecycle_reason: null,
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
        displayedEvidenceLabel: "Moderate evidence",
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
    expect(body.context.displayed_evidence_label).toBe("Moderate evidence");
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
  it("words evidence the same way everywhere, never as a number", () => {
    for (const label of ["High", "Moderate", "Low", "Speculative"] as const) {
      const text = evidenceLabelFor({ confidence_label: label });
      expect(text).toBe(`${label} evidence`);
      expect(text).not.toMatch(/[0-9%]/);
    }
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

  it("shows STRATUS TAKE only when there is something personal to say", () => {
    expect(stratusTakeFor(item())).toBe("You watch NVIDIA.");
    const generic = item();
    generic.delivered_item = { ...generic.delivered_item, why_it_matters_to_me: "  " };
    expect(stratusTakeFor(generic)).toBeNull();
  });

  it("qualifies data only when currency cannot be confirmed", () => {
    expect(freshnessNoticeFor("FRESH")).toBeNull();
    expect(freshnessNoticeFor("RECENTLY_OBSERVED")).toBeNull();
    expect(freshnessNoticeFor(null)).toBeNull();
    expect(freshnessNoticeFor("STALE_WITHIN_GRACE")).toMatch(/out of date/);
    expect(freshnessNoticeFor("UNAVAILABLE")).toMatch(/cannot currently confirm/);
  });
});
