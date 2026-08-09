// Symbol resolution pipeline: Canonical Entity -> Symbol Resolver -> ResolvedSymbol.
// Every Opportunity Node renders through this same lookup -- no per-entity
// components. When Logan encounters a new entity_id, this file (a data lookup, not
// new UI code) is the only thing that would ever need an entry, and even without
// one it degrades gracefully through the fallback chain below.
//
// Fallback order: known logo -> ticker -> known category icon -> initials.
// (Category icon is placed ahead of initials for entities like "NFL" or "FED" --
// their entity_id already reads like an acronym, so initials would just repeat the
// label under the node. A category icon carries more information in that case.)

export type ResolvedSymbol =
  | { kind: "logo"; iconName: string; color: string }
  | { kind: "ticker"; text: string; color: string }
  | { kind: "category"; iconName: string; color: string }
  | { kind: "initials"; text: string; color: string };

// FontAwesome5 brand icon names, for entities with a recognizable public logo.
const KNOWN_LOGOS: Record<string, string> = {
  AAPL: "apple",
  BTC: "bitcoin",
};

// FontAwesome5 solid icon names, one per category.
const CATEGORY_ICONS: Record<string, string> = {
  stocks: "chart-line",
  markets: "chart-line",
  commodities: "oil-can",
  crypto: "coins",
  macro: "university",
  sports: "football-ball",
  culture: "music",
  "prediction-markets": "balance-scale",
  technology: "microchip",
};

// V3.1.4.2 brand correction pass: this app's category taxonomy collapses
// onto the owner's reference "Markets / Odds / Trends" grouping (its color
// palette panel gives exact hex values for exactly those three, plus a
// neutral) -- not the wider per-category rainbow (teal/gold/violet/etc.)
// from the prior pass. STRATUS orange is reserved for brand chrome/active
// states and is never returned here, so it keeps meaning "this is STRATUS
// itself." Same-category entities share a color family and are told apart
// by ticker/icon/name, not by hue.
const CATEGORY_COLORS: Record<string, string> = {
  // Markets: muted green -- stocks, broad markets, commodities, technology,
  // and crypto (the reference shows BTC grouped under "MARKETS", not a
  // separate crypto hue).
  stocks: "#22C55E",
  markets: "#22C55E",
  commodities: "#22C55E",
  technology: "#22C55E",
  crypto: "#22C55E",
  // Odds: muted red -- sports and prediction markets are genuinely
  // wager/risk-adjacent, which is what muted red is reserved for.
  sports: "#EF4444",
  "prediction-markets": "#EF4444",
  // Trends: muted violet -- culture/social signals.
  culture: "#A78BFA",
};
// macro (e.g. Fed policy) has no clear home in Markets/Odds/Trends and
// isn't shown in the reference -- kept neutral rather than guessed.
const NEUTRAL_COLOR = "#9A9AA2";

function colorFor(category: string): string {
  return CATEGORY_COLORS[category] ?? NEUTRAL_COLOR;
}

function initialsFor(displayName: string): string {
  const words = displayName.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export function resolveSymbol(entity: {
  entity_id: string;
  display_name: string;
  category: string;
  ticker: string | null;
}): ResolvedSymbol {
  const color = colorFor(entity.category);

  const logo = KNOWN_LOGOS[entity.entity_id];
  if (logo) return { kind: "logo", iconName: logo, color };

  if (entity.ticker) return { kind: "ticker", text: entity.ticker, color };

  const categoryIcon = CATEGORY_ICONS[entity.category];
  if (categoryIcon) return { kind: "category", iconName: categoryIcon, color };

  return { kind: "initials", text: initialsFor(entity.display_name), color };
}
