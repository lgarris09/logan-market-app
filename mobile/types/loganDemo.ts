// Mirrors backend/app/logan_demo.py's TeslaDemoResponse and the logan_core
// contracts it wraps (DeliveredItem, ConclusionConfidence, PolicyResult).
// Field names match the Pydantic models' JSON serialization exactly.

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
};

export type ConclusionConfidence = {
  event_id: string;
  confidence_score: number;
  classification: "fact" | "inference" | "hypothesis" | "speculation";
  alternatives: string[];
  limiting_factors: string[];
  evaluated_at: string;
};

export type PolicyResult = {
  event_id: string;
  permitted: boolean;
  communication_mode: "analysis" | "alert" | "informational" | "suppressed";
  language_constraints: string[];
  required_disclaimers: string[];
  policy_rules_applied: string[];
  evaluated_at: string;
};

export type ExecutionTraceSummary = {
  pipeline_run_id: string;
  status: "running" | "complete" | "failed" | "partial";
  started_at: string;
  completed_at: string | null;
  total_layers: number;
  layers: string[];
  all_succeeded: boolean;
  total_latency_ms: number;
};

export type TeslaDemoResponse = {
  delivered_item: DeliveredItem;
  confidence: ConclusionConfidence;
  policy_result: PolicyResult;
  execution_trace: ExecutionTraceSummary;
};
