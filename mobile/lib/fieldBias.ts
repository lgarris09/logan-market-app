import { FeedItem } from "../types/loganFeed";

// FIELD BIAS: a temporary lens the user applies to the Attention Field, not
// a filter, not a screen, not a permanent user-model change. See the
// implementation brief for the full product spec. This file owns only the
// pure domain mapping (category -> bias group) and the match predicate --
// no presentation, no state.
export type FieldBias = "all" | "markets" | "odds" | "trends";

// Explicit, source-agnostic category -> FIELD BIAS group mapping, derived
// directly from the real FeedItem.category contract values (confirmed set:
// stocks, markets, commodities, crypto, macro, sports, culture,
// prediction-markets, technology -- see lib/symbolResolver.ts's
// CATEGORY_ICONS/CATEGORY_COLORS keys for the canonical taxonomy). This is
// intentionally NOT derived from CATEGORY_COLORS -- color is presentation
// metadata and may change independently of this semantic grouping. macro
// and any future/unmapped category correctly return null (stays neutral,
// never guessed).
const CATEGORY_GROUPS: Record<string, "markets" | "odds" | "trends"> = {
  stocks: "markets",
  markets: "markets",
  commodities: "markets",
  technology: "markets",
  crypto: "markets",
  sports: "odds",
  "prediction-markets": "odds",
  culture: "trends",
};

export function categoryGroup(category: string): "markets" | "odds" | "trends" | null {
  return CATEGORY_GROUPS[category] ?? null;
}

export type BiasVisualState = "neutral" | "emphasized" | "receded";

// The per-item presentation state for the active lens -- never a filter,
// every item still renders regardless of this value (see
// AttentionField.tsx / Vessel.tsx). "all" and any category with no group
// mapping (e.g. macro -- see symbolResolver.ts's CATEGORY_COLORS comment
// for the same "kept neutral rather than guessed" call on this exact
// category) both resolve to "neutral": an item Logan never confidently
// placed in a group must never be visually penalized (receded) for not
// matching one.
export function biasStateFor(item: FeedItem, bias: FieldBias): BiasVisualState {
  if (bias === "all") return "neutral";
  const group = categoryGroup(item.category);
  if (group === null) return "neutral";
  return group === bias ? "emphasized" : "receded";
}
