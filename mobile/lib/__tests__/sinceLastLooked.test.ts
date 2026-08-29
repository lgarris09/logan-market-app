import { SinceLastLookedSummary } from "../../types/loganFeed";
import { describeSinceLastLooked } from "../sinceLastLooked";

const BASE: SinceLastLookedSummary = {
  schema_version: "1.0",
  entity_id: "NVDA",
  user_id: "user-1",
  status: "first_view",
  change_type: null,
  detail: null,
  evaluated_at: "2026-08-29T00:00:00Z",
};

describe("describeSinceLastLooked", () => {
  it("renders nothing for a null/absent summary", () => {
    expect(describeSinceLastLooked(null)).toBeNull();
    expect(describeSinceLastLooked(undefined)).toBeNull();
  });

  it("renders nothing for first_view -- no fake since-you-last-looked language", () => {
    expect(describeSinceLastLooked(BASE)).toBeNull();
  });

  it("renders a quiet, honest reassurance for no_material_change", () => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "no_material_change",
      detail: "No major change since your last look. STRATUS is still monitoring.",
    });
    expect(result).not.toBeNull();
    expect(result?.tone).toBe("quiet");
    expect(result?.label).toBe("STILL MONITORING");
    expect(result?.text).toContain("still monitoring");
  });

  it("renders the degraded state truthfully, distinct from no_material_change", () => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "degraded",
      detail: "Live data was temporarily unavailable this check.",
    });
    expect(result).not.toBeNull();
    expect(result?.tone).toBe("degraded");
    expect(result?.label).toBe("LIVE DATA UNAVAILABLE");
    expect(result?.icon).toBe("cloud-offline-outline");
  });

  it("renders a prominent material_change summary with the backend's own detail text", () => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "material_change",
      change_type: "trajectory_strengthening",
      detail: "Trajectory strengthened.",
    });
    expect(result).not.toBeNull();
    expect(result?.tone).toBe("material");
    expect(result?.label).toBe("SINCE YOU LAST LOOKED");
    expect(result?.text).toBe("Trajectory strengthened.");
  });

  it.each([
    ["trajectory_strengthening", "trending-up-outline"],
    ["trajectory_reaccelerated", "trending-up-outline"],
    ["trajectory_weakening", "trending-down-outline"],
    ["trajectory_reversing", "swap-vertical-outline"],
    ["confidence_increased", "trending-up-outline"],
    ["confidence_decreased", "trending-down-outline"],
    ["new_signal_appeared", "flash-outline"],
    ["convergence_formed", "git-merge-outline"],
    ["reactivated", "refresh-outline"],
  ] as const)("maps change_type %s to icon %s", (changeType, icon) => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "material_change",
      change_type: changeType,
      detail: "Something changed.",
    });
    expect(result?.icon).toBe(icon);
  });

  it("falls back to a default icon for a change_type with no specific mapping", () => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "material_change",
      change_type: "personal_relevance_increased",
      detail: "Something changed.",
    });
    expect(result?.icon).toBe("swap-vertical-outline");
  });

  it("falls back to a default icon when change_type itself is null", () => {
    const result = describeSinceLastLooked({
      ...BASE,
      status: "material_change",
      change_type: null,
      detail: "STRATUS detected a meaningful change since your last look.",
    });
    expect(result?.icon).toBe("swap-vertical-outline");
    expect(result?.text).toContain("meaningful change");
  });
});
