// Consumer Learning Controls (STRATUS 3.6.12 V1a closeout) -- the
// mobile-side entry point into GET /v1/learning/summary and POST
// /v1/learning/suppress (see backend/app/main.py, backend/app/learning.py).
//
// Deliberately a thin, consumer-safe surface: mirrors exactly what the
// backend's ConsumerLearningSummary/ConsumerLearningTrait contracts expose
// (backend/app/models.py) -- plain description, explicit/inferred basis,
// whether a trait can be suppressed. No raw strength float, evidence count,
// or timestamp reaches this file, because the backend never sends one.
// UI exposure only -- this file makes no learning/ranking decisions itself.
import { fetchJson } from "./apiClient";

export type LearningTraitBasis = "explicit" | "inferred";

export type LearningTrait = {
  entityId: string;
  description: string;
  basis: LearningTraitBasis;
  canSuppress: boolean;
};

export type LearningSummary = {
  generatedAt: string;
  traits: LearningTrait[];
  explanation: string;
};

type LearningSummaryResponse = {
  schema_version: string;
  user_id: string;
  generated_at: string;
  traits: {
    entity_id: string;
    description: string;
    basis: LearningTraitBasis;
    can_suppress: boolean;
  }[];
  explanation: string;
};

/** Returns null on any failure (network, timeout, server error) -- the
 * screen renders a friendly failure state rather than a fetch error. */
export async function getLearningSummary(): Promise<LearningSummary | null> {
  const result = await fetchJson<LearningSummaryResponse>("/v1/learning/summary");
  if (result.status !== "success") {
    return null;
  }
  return {
    generatedAt: result.data.generated_at,
    traits: result.data.traits.map((t) => ({
      entityId: t.entity_id,
      description: t.description,
      basis: t.basis,
      canSuppress: t.can_suppress,
    })),
    explanation: result.data.explanation,
  };
}

/**
 * "Stop using this reason" -- suppresses whatever STRATUS currently infers
 * about `entityId` for this user, going forward. Never deletes objective
 * opportunity data; only affects this user's own personal-relevance
 * weighting (see logan_core/learning/engine.py's suppress_entity()).
 * Returns true only on a confirmed backend suppression -- the caller
 * (learning.tsx) re-fetches the summary afterward rather than guessing at
 * the new list locally, since a suppressed trait can affect more than
 * itself (e.g. a shared underlying interest).
 */
export async function suppressLearningReason(entityId: string): Promise<boolean> {
  const result = await fetchJson<{ entity_id: string; suppressed: boolean }>(
    "/v1/learning/suppress",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entity_id: entityId }),
      retries: 0, // non-idempotent-in-effect intent; a retried POST after a real success is still safe server-side (idempotent correction), but this file doesn't need to assume that
    }
  );
  return result.status === "success" && result.data.suppressed === true;
}
